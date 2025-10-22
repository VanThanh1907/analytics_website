from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import redis
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeRecommendationEngine:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("RealTimeRecommendationEngine") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.streaming.stopGracefullyOnShutdown", "true") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        # Kết nối Redis
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        
        logger.info("Real-time Recommendation Engine đã khởi tạo")

    def process_streaming_events(self):
        """Xử lý events streaming từ Kafka"""
        logger.info("Bắt đầu xử lý streaming events...")
        
        # Đọc từ Kafka
        kafka_df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "kafka:29092") \
            .option("subscribe", "spark_processing") \
            .option("startingOffsets", "latest") \
            .load()
        
        # Parse JSON data
        schema = StructType([
            StructField("user_id", IntegerType(), True),
            StructField("event_type", StringType(), True),
            StructField("data", MapType(StringType(), StringType()), True),
            StructField("timestamp", StringType(), True)
        ])
        
        parsed_df = kafka_df.select(
            from_json(col("value").cast("string"), schema).alias("event")
        ).select("event.*")
        
        # Xử lý real-time recommendations
        query = parsed_df.writeStream \
            .foreachBatch(self.update_recommendations) \
            .outputMode("append") \
            .trigger(processingTime='30 seconds') \
            .start()
        
        query.awaitTermination()

    def update_recommendations(self, batch_df, batch_id):
        """Cập nhật recommendations real-time"""
        if batch_df.count() == 0:
            return
        
        logger.info(f"Xử lý batch {batch_id} với {batch_df.count()} events")
        
        # Lọc các events quan trọng
        important_events = batch_df.filter(
            col("event_type").isin([
                "product_view", 
                "click", 
                "recommendation_click",
                "search"
            ])
        )
        
        if important_events.count() == 0:
            return
        
        # Group by user để xử lý
        user_events = important_events.groupBy("user_id").agg(
            collect_list("event_type").alias("event_types"),
            collect_list("data").alias("event_data")
        )
        
        # Xử lý từng user
        users_data = user_events.collect()
        
        for row in users_data:
            user_id = row['user_id']
            event_types = row['event_types']
            event_data = row['event_data']
            
            # Cập nhật recommendations cho user này
            self.update_user_recommendations(user_id, event_types, event_data)

    def update_user_recommendations(self, user_id, event_types, event_data):
        """Cập nhật recommendations cho một user cụ thể"""
        try:
            # Lấy recommendations hiện tại
            current_recs_key = f"recommendations:user:{user_id}"
            current_recs = self.redis_client.get(current_recs_key)
            
            if current_recs:
                current_recs = json.loads(current_recs)
            else:
                current_recs = []
            
            # Phân tích events mới
            new_interests = self.extract_user_interests(event_types, event_data)
            
            # Lấy sản phẩm tương tự dựa trên interests mới
            similar_products = self.find_similar_products(new_interests)
            
            # Merge với recommendations hiện tại
            updated_recs = self.merge_recommendations(current_recs, similar_products)
            
            # Lưu vào Redis
            self.redis_client.set(current_recs_key, json.dumps(updated_recs))
            self.redis_client.expire(current_recs_key, 86400 * 3)  # 3 ngày
            
            logger.info(f"Đã cập nhật recommendations cho user {user_id}")
            
        except Exception as e:
            logger.error(f"Lỗi cập nhật recommendations cho user {user_id}: {e}")

    def extract_user_interests(self, event_types, event_data):
        """Trích xuất sở thích từ events"""
        interests = {
            'categories': {},
            'price_ranges': {},
            'recent_products': []
        }
        
        for i, event_type in enumerate(event_types):
            data = event_data[i] if i < len(event_data) else {}
            
            if event_type in ['product_view', 'click', 'recommendation_click']:
                # Trích xuất category
                category = data.get('category')
                if category:
                    interests['categories'][category] = interests['categories'].get(category, 0) + 1
                
                # Trích xuất price range
                price = data.get('price')
                if price:
                    try:
                        price_float = float(price)
                        price_range = self.get_price_range(price_float)
                        interests['price_ranges'][price_range] = interests['price_ranges'].get(price_range, 0) + 1
                    except:
                        pass
                
                # Lưu recent products
                product_id = data.get('product_id')
                if product_id and product_id not in interests['recent_products']:
                    interests['recent_products'].append(product_id)
        
        return interests

    def get_price_range(self, price):
        """Phân loại khoảng giá"""
        if price < 1000000:
            return 'under_1m'
        elif price < 5000000:
            return '1m_5m'
        elif price < 10000000:
            return '5m_10m'
        elif price < 20000000:
            return '10m_20m'
        else:
            return 'over_20m'

    def find_similar_products(self, interests):
        """Tìm sản phẩm tương tự dựa trên interests"""
        similar_products = []
        
        # Lấy sản phẩm trending
        trending_products = self.redis_client.get("trending_products")
        if trending_products:
            trending_products = json.loads(trending_products)
            similar_products.extend(trending_products[:5])
        
        # Lấy sản phẩm theo category yêu thích
        for category, count in interests['categories'].items():
            category_products = self.redis_client.get(f"category_products:{category}")
            if category_products:
                category_products = json.loads(category_products)
                similar_products.extend(category_products[:3])
        
        # Loại bỏ trùng lặp và recent products
        similar_products = list(set(similar_products))
        for product_id in interests['recent_products']:
            if product_id in similar_products:
                similar_products.remove(product_id)
        
        return similar_products[:10]

    def merge_recommendations(self, current_recs, new_recs):
        """Merge recommendations hiện tại với recommendations mới"""
        # Kết hợp và sắp xếp lại
        all_recs = new_recs + current_recs
        
        # Loại bỏ trùng lặp nhưng giữ thứ tự
        unique_recs = []
        seen = set()
        
        for rec in all_recs:
            if rec not in seen:
                unique_recs.append(rec)
                seen.add(rec)
        
        return unique_recs[:15]  # Giữ tối đa 15 recommendations

    def start_streaming(self):
        """Khởi động streaming processing"""
        try:
            self.process_streaming_events()
        except Exception as e:
            logger.error(f"Lỗi streaming: {e}")
        finally:
            self.spark.stop()

def main():
    engine = RealTimeRecommendationEngine()
    engine.start_streaming()

if __name__ == "__main__":
    main()