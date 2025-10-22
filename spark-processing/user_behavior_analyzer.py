from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
import json
import redis
import psycopg2
from datetime import datetime, timedelta
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserBehaviorAnalyzer:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("UserBehaviorAnalyzer") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        # Kết nối PostgreSQL
        self.db_url = "postgresql://admin:password123@postgres:5432/ecommerce_db"
        self.db_properties = {
            "user": "admin",
            "password": "password123",
            "driver": "org.postgresql.Driver"
        }
        
        # Kết nối Redis
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        
        logger.info("User Behavior Analyzer đã khởi tạo")

    def load_user_interactions(self):
        """Tải dữ liệu tương tác người dùng từ database"""
        query = """
        (SELECT 
            ui.user_id,
            ui.product_id,
            ui.interaction_type,
            ui.details,
            ui.timestamp,
            p.category,
            p.price,
            p.name as product_name
        FROM user_interaction ui
        JOIN product p ON ui.product_id = p.id
        WHERE ui.timestamp >= NOW() - INTERVAL '30 days'
        ) as interactions
        """
        
        df = self.spark.read.jdbc(
            url=self.db_url,
            table=query,
            properties=self.db_properties
        )
        
        return df

    def load_raw_events(self):
        """Tải raw events từ Kafka processing"""
        query = """
        (SELECT 
            user_id,
            event_type,
            event_data,
            timestamp
        FROM raw_events
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        ) as events
        """
        
        df = self.spark.read.jdbc(
            url=self.db_url,
            table=query,
            properties=self.db_properties
        )
        
        return df

    def analyze_user_preferences(self):
        """Phân tích sở thích người dùng"""
        logger.info("Bắt đầu phân tích sở thích người dùng...")
        
        interactions_df = self.load_user_interactions()
        
        # Tính điểm tương tác cho mỗi user-product
        interaction_scores = interactions_df.select(
            "user_id",
            "product_id", 
            "interaction_type",
            "category",
            "price"
        ).withColumn(
            "score",
            when(col("interaction_type") == "view", 1.0)
            .when(col("interaction_type") == "click", 2.0)
            .when(col("interaction_type") == "click_add_to_cart", 5.0)
            .when(col("interaction_type") == "recommendation_click", 3.0)
            .otherwise(1.0)
        )
        
        # Tổng hợp điểm theo user-product
        user_product_scores = interaction_scores.groupBy("user_id", "product_id") \
            .agg(
                sum("score").alias("total_score"),
                first("category").alias("category"),
                first("price").alias("price")
            )
        
        # Phân tích sở thích category
        category_preferences = interaction_scores.groupBy("user_id", "category") \
            .agg(
                sum("score").alias("category_score"),
                count("*").alias("interaction_count")
            )
        
        # Lưu vào Redis
        self.save_user_preferences_to_redis(category_preferences)
        
        return user_product_scores

    def save_user_preferences_to_redis(self, category_preferences_df):
        """Lưu sở thích người dùng vào Redis"""
        logger.info("Lưu sở thích người dùng vào Redis...")
        
        # Collect dữ liệu và lưu vào Redis
        preferences = category_preferences_df.collect()
        
        for row in preferences:
            user_id = row['user_id']
            category = row['category']
            score = row['category_score']
            
            # Lưu vào Redis với key pattern user_preferences:user_id
            redis_key = f"user_preferences:{user_id}"
            self.redis_client.hset(redis_key, category, score)
            self.redis_client.expire(redis_key, 86400 * 7)  # 7 ngày

    def build_collaborative_filtering_model(self):
        """Xây dựng mô hình Collaborative Filtering bằng ALS"""
        logger.info("Xây dựng mô hình Collaborative Filtering...")
        
        user_product_scores = self.analyze_user_preferences()
        
        # Chuẩn bị dữ liệu cho ALS
        # ALS yêu cầu user_id và product_id là số nguyên
        training_data = user_product_scores.select(
            col("user_id").cast("integer").alias("user"),
            col("product_id").cast("integer").alias("item"), 
            col("total_score").cast("float").alias("rating")
        ).filter(col("rating") > 0)
        
        # Chia dữ liệu training/test
        (training, test) = training_data.randomSplit([0.8, 0.2], seed=42)
        
        # Xây dựng mô hình ALS
        als = ALS(
            maxIter=10,
            regParam=0.1,
            userCol="user",
            itemCol="item",
            ratingCol="rating",
            coldStartStrategy="drop",
            seed=42
        )
        
        model = als.fit(training)
        
        # Đánh giá mô hình
        predictions = model.transform(test)
        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol="rating",
            predictionCol="prediction"
        )
        rmse = evaluator.evaluate(predictions)
        logger.info(f"RMSE của mô hình: {rmse}")
        
        # Tạo recommendations cho tất cả users
        self.generate_recommendations(model, training_data)
        
        return model

    def generate_recommendations(self, model, training_data):
        """Tạo gợi ý cho tất cả người dùng"""
        logger.info("Tạo gợi ý cho người dùng...")
        
        # Lấy danh sách unique users
        unique_users = training_data.select("user").distinct()
        
        # Tạo recommendations cho mỗi user (top 10)
        user_recommendations = model.recommendForAllUsers(10)
        
        # Chuyển đổi format và lưu vào Redis
        recommendations_data = user_recommendations.collect()
        
        for row in recommendations_data:
            user_id = row['user']
            recommendations = [rec['item'] for rec in row['recommendations']]
            
            # Lưu vào Redis
            redis_key = f"recommendations:user:{user_id}"
            self.redis_client.set(redis_key, json.dumps(recommendations))
            self.redis_client.expire(redis_key, 86400 * 3)  # 3 ngày

    def analyze_product_trends(self):
        """Phân tích xu hướng sản phẩm"""
        logger.info("Phân tích xu hướng sản phẩm...")
        
        interactions_df = self.load_user_interactions()
        
        # Phân tích sản phẩm hot trong 7 ngày qua
        recent_interactions = interactions_df.filter(
            col("timestamp") >= (current_timestamp() - expr("INTERVAL 7 DAYS"))
        )
        
        # Tính điểm trending
        trending_products = recent_interactions.groupBy("product_id", "product_name", "category") \
            .agg(
                countDistinct("user_id").alias("unique_users"),
                count("*").alias("total_interactions"),
                sum(
                    when(col("interaction_type") == "view", 1)
                    .when(col("interaction_type") == "click", 3)
                    .when(col("interaction_type") == "click_add_to_cart", 10)
                    .otherwise(1)
                ).alias("trending_score")
            ) \
            .orderBy(desc("trending_score")) \
            .limit(20)
        
        # Lưu trending products vào Redis
        self.save_trending_products(trending_products)
        
        return trending_products

    def save_trending_products(self, trending_df):
        """Lưu sản phẩm trending vào Redis"""
        trending_data = trending_df.collect()
        
        trending_product_ids = [row['product_id'] for row in trending_data]
        
        # Lưu vào Redis
        self.redis_client.set("trending_products", json.dumps(trending_product_ids))
        self.redis_client.expire("trending_products", 86400)  # 1 ngày

    def analyze_user_segments(self):
        """Phân đoạn người dùng dựa trên hành vi"""
        logger.info("Phân đoạn người dùng...")
        
        interactions_df = self.load_user_interactions()
        
        # Tính toán metrics cho mỗi user
        user_metrics = interactions_df.groupBy("user_id") \
            .agg(
                count("*").alias("total_interactions"),
                countDistinct("product_id").alias("unique_products"),
                avg("price").alias("avg_price_interest"),
                countDistinct("category").alias("categories_explored"),
                sum(
                    when(col("interaction_type").contains("click"), 1).otherwise(0)
                ).alias("click_count"),
                sum(
                    when(col("interaction_type") == "view", 1).otherwise(0)
                ).alias("view_count")
            )
        
        # Tính click-through rate
        user_metrics = user_metrics.withColumn(
            "ctr",
            when(col("view_count") > 0, col("click_count") / col("view_count")).otherwise(0)
        )
        
        # Phân đoạn users
        user_segments = user_metrics.withColumn(
            "segment",
            when((col("total_interactions") >= 50) & (col("ctr") >= 0.1), "high_engagement")
            .when((col("total_interactions") >= 20) & (col("ctr") >= 0.05), "medium_engagement")
            .when(col("total_interactions") >= 5, "low_engagement")
            .otherwise("new_user")
        )
        
        # Lưu segments vào Redis
        self.save_user_segments(user_segments)
        
        return user_segments

    def save_user_segments(self, segments_df):
        """Lưu phân đoạn người dùng vào Redis"""
        segments_data = segments_df.select("user_id", "segment").collect()
        
        for row in segments_data:
            user_id = row['user_id']
            segment = row['segment']
            
            redis_key = f"user_segment:{user_id}"
            self.redis_client.set(redis_key, segment)
            self.redis_client.expire(redis_key, 86400 * 7)  # 7 ngày

    def run_analysis_pipeline(self):
        """Chạy toàn bộ pipeline phân tích"""
        logger.info("Bắt đầu pipeline phân tích hành vi người dùng...")
        
        try:
            # 1. Phân tích sở thích người dùng
            self.analyze_user_preferences()
            
            # 2. Xây dựng mô hình Collaborative Filtering
            self.build_collaborative_filtering_model()
            
            # 3. Phân tích xu hướng sản phẩm
            self.analyze_product_trends()
            
            # 4. Phân đoạn người dùng
            self.analyze_user_segments()
            
            logger.info("Hoàn thành pipeline phân tích!")
            
        except Exception as e:
            logger.error(f"Lỗi trong pipeline phân tích: {e}")
            raise
        
        finally:
            self.spark.stop()

def main():
    analyzer = UserBehaviorAnalyzer()
    analyzer.run_analysis_pipeline()

if __name__ == "__main__":
    main()