from kafka import KafkaConsumer, KafkaProducer
import json
import logging
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import redis

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KafkaEventProcessor:
    def __init__(self):
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://admin:password123@localhost:5432/ecommerce_db')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # Khởi tạo Kafka consumer
        self.consumer = KafkaConsumer(
            'user_events',
            bootstrap_servers=[self.kafka_bootstrap_servers],
            auto_offset_reset='latest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='event_processor_group'
        )
        
        # Khởi tạo Kafka producer cho processed events
        self.producer = KafkaProducer(
            bootstrap_servers=[self.kafka_bootstrap_servers],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Kết nối database
        self.db_conn = psycopg2.connect(self.db_url)
        
        # Kết nối Redis
        self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        
        logger.info("Kafka Event Processor đã khởi tạo thành công")

    def process_events(self):
        """Xử lý các event từ Kafka"""
        logger.info("Bắt đầu lắng nghe events từ Kafka...")
        
        for message in self.consumer:
            try:
                event = message.value
                logger.info(f"Nhận được event: {event}")
                
                # Xử lý event dựa trên loại
                self.handle_event(event)
                
            except Exception as e:
                logger.error(f"Lỗi xử lý event: {e}")

    def handle_event(self, event):
        """Xử lý từng loại event cụ thể"""
        event_type = event.get('event_type')
        user_id = event.get('user_id')
        data = event.get('data', {})
        timestamp = event.get('timestamp')
        
        # Lưu raw event vào database
        self.save_raw_event(event)
        
        # Xử lý theo từng loại event
        if event_type == 'product_view':
            self.handle_product_view(user_id, data, timestamp)
        elif event_type == 'search':
            self.handle_search(user_id, data, timestamp)
        elif event_type == 'click':
            self.handle_click(user_id, data, timestamp)
        elif event_type == 'product_card_click':
            self.handle_product_card_click(user_id, data, timestamp)
        elif event_type == 'recommendation_click':
            self.handle_recommendation_click(user_id, data, timestamp)
        elif event_type == 'page_view':
            self.handle_page_view(user_id, data, timestamp)
        
        # Cập nhật user profile
        self.update_user_profile(user_id, event_type, data)
        
        # Gửi processed event để Spark xử lý
        self.send_to_spark_processing(event)

    def save_raw_event(self, event):
        """Lưu raw event vào database"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO raw_events (user_id, event_type, event_data, timestamp)
                    VALUES (%s, %s, %s, %s)
                """, (
                    event.get('user_id'),
                    event.get('event_type'),
                    json.dumps(event),
                    event.get('timestamp')
                ))
                self.db_conn.commit()
        except Exception as e:
            logger.error(f"Lỗi lưu raw event: {e}")
            self.db_conn.rollback()

    def handle_product_view(self, user_id, data, timestamp):
        """Xử lý sự kiện xem sản phẩm"""
        product_id = data.get('product_id')
        
        # Cập nhật thống kê sản phẩm
        self.update_product_stats(product_id, 'view')
        
        # Lưu vào user interaction history
        self.save_user_interaction(user_id, product_id, 'view', data)
        
        # Cập nhật recent views trong Redis
        recent_views_key = f"user:{user_id}:recent_views"
        self.redis_client.lpush(recent_views_key, product_id)
        self.redis_client.ltrim(recent_views_key, 0, 49)  # Giữ 50 item gần nhất
        self.redis_client.expire(recent_views_key, 86400 * 7)  # 7 ngày

    def handle_search(self, user_id, data, timestamp):
        """Xử lý sự kiện tìm kiếm"""
        query = data.get('query')
        results_count = data.get('results_count', 0)
        
        # Lưu search history
        search_key = f"user:{user_id}:search_history"
        search_data = {
            'query': query,
            'results_count': results_count,
            'timestamp': timestamp
        }
        self.redis_client.lpush(search_key, json.dumps(search_data))
        self.redis_client.ltrim(search_key, 0, 99)  # Giữ 100 tìm kiếm gần nhất
        self.redis_client.expire(search_key, 86400 * 30)  # 30 ngày

    def handle_click(self, user_id, data, timestamp):
        """Xử lý sự kiện click"""
        action = data.get('action')
        product_id = data.get('product_id')
        
        if action and product_id:
            self.save_user_interaction(user_id, product_id, f'click_{action}', data)
            self.update_product_stats(product_id, action)

    def handle_product_card_click(self, user_id, data, timestamp):
        """Xử lý click vào card sản phẩm"""
        product_id = data.get('product_id')
        is_recommendation = data.get('is_recommendation', False)
        
        if product_id:
            interaction_type = 'card_click_recommendation' if is_recommendation else 'card_click'
            self.save_user_interaction(user_id, product_id, interaction_type, data)

    def handle_recommendation_click(self, user_id, data, timestamp):
        """Xử lý click vào sản phẩm được gợi ý"""
        product_id = data.get('product_id')
        
        if product_id:
            self.save_user_interaction(user_id, product_id, 'recommendation_click', data)
            
            # Cập nhật thống kê hiệu quả của recommendation
            rec_stats_key = f"recommendation_stats:{product_id}"
            self.redis_client.hincrby(rec_stats_key, 'clicks', 1)
            self.redis_client.expire(rec_stats_key, 86400 * 7)

    def handle_page_view(self, user_id, data, timestamp):
        """Xử lý sự kiện xem trang"""
        page = data.get('page')
        
        # Lưu page view history
        page_views_key = f"user:{user_id}:page_views"
        page_data = {
            'page': page,
            'timestamp': timestamp
        }
        self.redis_client.lpush(page_views_key, json.dumps(page_data))
        self.redis_client.ltrim(page_views_key, 0, 199)  # Giữ 200 page view gần nhất
        self.redis_client.expire(page_views_key, 86400 * 7)  # 7 ngày

    def save_user_interaction(self, user_id, product_id, interaction_type, details):
        """Lưu user interaction vào database"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_interaction (user_id, product_id, interaction_type, details, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (user_id, product_id, interaction_type, json.dumps(details)))
                self.db_conn.commit()
        except Exception as e:
            logger.error(f"Lỗi lưu user interaction: {e}")
            self.db_conn.rollback()

    def update_product_stats(self, product_id, action):
        """Cập nhật thống kê sản phẩm"""
        stats_key = f"product_stats:{product_id}"
        self.redis_client.hincrby(stats_key, action, 1)
        self.redis_client.hincrby(stats_key, 'total_interactions', 1)
        self.redis_client.expire(stats_key, 86400 * 30)  # 30 ngày

    def update_user_profile(self, user_id, event_type, data):
        """Cập nhật profile người dùng dựa trên hành vi"""
        profile_key = f"user_profile:{user_id}"
        
        # Cập nhật category preferences
        if event_type in ['product_view', 'click', 'recommendation_click']:
            category = data.get('category')
            if category:
                category_key = f"user_profile:{user_id}:categories"
                self.redis_client.hincrby(category_key, category, 1)
                self.redis_client.expire(category_key, 86400 * 30)
        
        # Cập nhật price range preferences
        if event_type in ['product_view', 'click']:
            price = data.get('price')
            if price:
                price_range = self.get_price_range(price)
                price_key = f"user_profile:{user_id}:price_ranges"
                self.redis_client.hincrby(price_key, price_range, 1)
                self.redis_client.expire(price_key, 86400 * 30)

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

    def send_to_spark_processing(self, event):
        """Gửi event tới topic để Spark xử lý"""
        try:
            # Gửi tới topic khác để Spark consume
            self.producer.send('spark_processing', value=event)
            self.producer.flush()
        except Exception as e:
            logger.error(f"Lỗi gửi event tới Spark: {e}")

def main():
    # Tạo bảng cần thiết
    create_tables()
    
    # Khởi tạo processor
    processor = KafkaEventProcessor()
    
    try:
        processor.process_events()
    except KeyboardInterrupt:
        logger.info("Dừng Event Processor...")
    finally:
        processor.db_conn.close()

def create_tables():
    """Tạo các bảng cần thiết"""
    db_url = os.getenv('DATABASE_URL', 'postgresql://admin:password123@localhost:5432/ecommerce_db')
    
    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cursor:
            # Tạo bảng raw_events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raw_events (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    event_type VARCHAR(100),
                    event_data JSONB,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Tạo index
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_raw_events_user_id ON raw_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_raw_events_event_type ON raw_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_raw_events_timestamp ON raw_events(timestamp);
            """)
            
        conn.commit()
        conn.close()
        logger.info("Đã tạo bảng thành công")
    except Exception as e:
        logger.error(f"Lỗi tạo bảng: {e}")

if __name__ == "__main__":
    main()