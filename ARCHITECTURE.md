# Cấu trúc dự án E-commerce Analytics

```
final-project/
├── 📁 web-app/                    # Ứng dụng web Flask
│   ├── 📄 app.py                  # Main Flask application
│   ├── 📄 Dockerfile              # Docker config cho web app
│   ├── 📄 requirements.txt        # Python dependencies
│   ├── 📁 templates/              # HTML templates
│   │   ├── 📄 base.html           # Base template
│   │   ├── 📄 index.html          # Trang chủ
│   │   ├── 📄 login.html          # Trang đăng nhập
│   │   ├── 📄 register.html       # Trang đăng ký
│   │   ├── 📄 product_detail.html # Chi tiết sản phẩm
│   │   ├── 📄 search_results.html # Kết quả tìm kiếm
│   │   └── 📄 recommendations.html # Trang gợi ý
│   └── 📁 static/                 # Static files
│       ├── 📁 css/
│       │   └── 📄 style.css       # Custom CSS
│       └── 📁 js/
│           └── 📄 tracking.js     # User tracking JavaScript
│
├── 📁 kafka-config/               # Kafka event processing
│   ├── 📄 event_processor.py      # Kafka consumer & processor
│   ├── 📄 Dockerfile              # Docker config
│   └── 📄 requirements.txt        # Python dependencies
│
├── 📁 spark-processing/           # Spark analytics jobs
│   ├── 📄 user_behavior_analyzer.py    # Batch analytics job
│   ├── 📄 realtime_recommendation.py   # Real-time processing
│   └── 📄 requirements.txt        # Python dependencies
│
├── 📁 recommendation-engine/      # Recommendation system
│   ├── 📄 recommendation_api.py    # Hybrid recommendation engine
│   └── 📄 requirements.txt        # Python dependencies
│
├── 📁 docker/                     # Docker configurations
│   └── (additional docker configs if needed)
│
├── 📄 docker-compose.yml          # Docker Compose configuration
├── 📄 start_pipeline.sh           # Startup script (Linux/Mac)
├── 📄 start_pipeline.bat          # Startup script (Windows)
├── 📄 README.md                   # Tài liệu chính
└── 📄 ARCHITECTURE.md             # Tài liệu này
```

## 🏗️ Architecture Overview

### Data Flow
```
User Browser
    ↓ (HTTP Requests + JavaScript Events)
Flask Web App
    ↓ (Kafka Messages)
Kafka Cluster
    ↓ (Stream Processing)
┌─────────────────┬─────────────────┐
│ Event Processor │ Spark Streaming │
│ (Python)        │ (PySpark)       │
└─────────────────┴─────────────────┘
    ↓                      ↓
PostgreSQL Database    Redis Cache
    ↓                      ↓
Spark Batch Jobs ←→ Recommendation Engine
    ↓                      ↓
ML Models (ALS) ←→ Hybrid Recommendations
```

### Components Interaction

1. **Web Layer**
   - Flask app serves web pages
   - JavaScript tracks user interactions
   - Events sent to Kafka via REST API

2. **Streaming Layer**  
   - Kafka handles real-time event streaming
   - Multiple topics for different event types
   - Event processor normalizes and stores data

3. **Processing Layer**
   - Spark batch jobs for ML model training
   - Real-time Spark streaming for instant updates
   - Redis caching for fast data retrieval

4. **ML Layer**
   - Collaborative Filtering with ALS
   - Content-based filtering
   - Hybrid recommendation engine
   - Real-time model updates

## 🔧 Technical Details

### Database Schema

**Users Table**
```sql
CREATE TABLE user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(120) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Products Table**
```sql
CREATE TABLE product (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price FLOAT NOT NULL,
    category VARCHAR(100),
    image_url VARCHAR(500),
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**User Interactions Table**
```sql
CREATE TABLE user_interaction (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES user(id),
    product_id INTEGER REFERENCES product(id),
    interaction_type VARCHAR(50) NOT NULL,
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

**Raw Events Table**
```sql
CREATE TABLE raw_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    event_type VARCHAR(100),
    event_data JSONB,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Kafka Topics

1. **user_events**
   - Raw user interaction events
   - Partitions: 3
   - Retention: 7 days

2. **spark_processing**
   - Processed events for Spark streaming
   - Partitions: 3  
   - Retention: 3 days

### Redis Keys Pattern

```
user_preferences:{user_id}        # User category preferences
recommendations:user:{user_id}    # Cached recommendations  
user:{user_id}:recent_views      # Recent product views
user:{user_id}:search_history    # Search history
product_stats:{product_id}       # Product interaction stats
trending_products                # Trending product IDs
user_segment:{user_id}           # User segment classification
```

### ML Pipeline

1. **Data Collection**
   - User interactions tracked via JavaScript
   - Events streamed through Kafka
   - Raw data stored in PostgreSQL

2. **Feature Engineering**
   - User-item interaction matrix
   - Product content features (category, price range)
   - User behavior features (CTR, session duration)

3. **Model Training**
   - ALS (Alternating Least Squares) for Collaborative Filtering
   - Content similarity using TF-IDF
   - Popularity ranking based on recent interactions

4. **Recommendation Generation**
   - Hybrid approach combining 4 methods:
     - Collaborative Filtering (40%)
     - Content-based (30%) 
     - Popularity-based (20%)
     - Behavior-based (10%)

5. **Real-time Updates**
   - Spark Streaming for instant recommendation updates
   - Redis caching for sub-second response times

## 🚀 Deployment

### Docker Services

1. **Infrastructure**
   - `zookeeper`: Kafka coordination
   - `kafka`: Message streaming
   - `postgres`: Primary database
   - `redis`: Caching layer

2. **Application** 
   - `web-app`: Flask web application
   - `kafka-processor`: Event processing
   - `spark-master`: Spark cluster master
   - `spark-worker`: Spark worker nodes

3. **Analytics**
   - `batch-processor`: Scheduled ML jobs
   - `realtime-processor`: Streaming analytics

### Scaling Considerations

- **Horizontal scaling**: Add more Spark workers
- **Kafka partitioning**: Increase partitions for higher throughput  
- **Redis clustering**: Use Redis Cluster for larger datasets
- **Database sharding**: Partition by user_id for large user bases

## 🔍 Monitoring

### Key Metrics

1. **Web Application**
   - Response time, error rate
   - User session duration
   - Conversion rates

2. **Kafka**
   - Message throughput
   - Consumer lag
   - Topic partition distribution

3. **Spark**
   - Job execution time
   - Resource utilization
   - Model accuracy (RMSE)

4. **Recommendations**
   - Click-through rate on recommendations
   - Recommendation diversity
   - Coverage metrics

### Health Checks

```bash
# Web app health
curl http://localhost:5000/health

# Kafka topic status  
docker exec kafka kafka-topics --describe --bootstrap-server localhost:9092

# Spark cluster status
curl http://localhost:8080/api/v1/applications

# Redis status
docker exec redis redis-cli ping
```

## 🔧 Configuration

### Environment-specific Settings

**Development**
```yaml
DEBUG: true
KAFKA_AUTO_OFFSET_RESET: earliest
SPARK_EXECUTOR_MEMORY: 1g
CACHE_TTL: 300  # 5 minutes
```

**Production**  
```yaml
DEBUG: false
KAFKA_AUTO_OFFSET_RESET: latest
SPARK_EXECUTOR_MEMORY: 4g
CACHE_TTL: 3600  # 1 hour
```

### Tuning Parameters

**Kafka Producer**
```python
producer_config = {
    'batch_size': 16384,
    'linger_ms': 10,
    'compression_type': 'gzip'
}
```

**Spark ALS Model**
```python
als_params = {
    'rank': 50,           # Number of latent factors
    'maxIter': 10,        # Maximum iterations
    'regParam': 0.1,      # Regularization parameter
    'alpha': 1.0          # Confidence parameter
}
```

**Recommendation Weights**
```python
hybrid_weights = {
    'collaborative': 0.4,
    'content': 0.3, 
    'popularity': 0.2,
    'behavior': 0.1
}
```

---

Tài liệu này cung cấp cái nhìn tổng quan về kiến trúc và cách thức hoạt động của hệ thống. Để biết thêm chi tiết implementation, tham khảo source code trong từng thư mục component.