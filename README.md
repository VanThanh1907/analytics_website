# 🛒 E-commerce Analytics với Kafka & Spark

Dự án e-commerce với hệ thống phân tích hành vi người dùng real-time sử dụng Apache Kafka và Apache Spark để tạo gợi ý sản phẩm cá nhân hóa.

## 🎯 Tính năng chính

### Web Application
- ✅ Cửa hàng trực tuyến cơ bản với đăng ký/đăng nhập
- ✅ Catalog sản phẩm với tìm kiếm
- ✅ Theo dõi hành vi người dùng (clicks, views, searches)
- ✅ Gợi ý sản phẩm cá nhân hóa cho từng user

### Analytics Pipeline
- ✅ **Apache Kafka**: Stream events người dùng real-time
- ✅ **Apache Spark**: Phân tích hành vi và xây dựng mô hình ML
- ✅ **Redis**: Cache kết quả và lưu user profiles
- ✅ **PostgreSQL**: Lưu trữ dữ liệu structured

### Machine Learning
- ✅ **Collaborative Filtering**: Sử dụng ALS (Alternating Least Squares)
- ✅ **Content-based Filtering**: Dựa trên category và features sản phẩm
- ✅ **Hybrid Recommendations**: Kết hợp nhiều phương pháp
- ✅ **Real-time Updates**: Cập nhật gợi ý theo thời gian thực

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────┐    ┌─────────────┐    ┌──────────────┐
│ Web App     │───▶│  Kafka   │───▶│ Spark       │───▶│ Redis Cache  │
│ (Flask)     │    │ Events   │    │ Processing  │    │ (Results)    │
└─────────────┘    └──────────┘    └─────────────┘    └──────────────┘
       │                                  │                    │
       │                                  │                    │
       ▼                                  ▼                    ▼
┌─────────────┐                    ┌─────────────┐    ┌──────────────┐
│ PostgreSQL  │◀───────────────────│ Analytics   │───▶│ Recommendation│
│ (Database)  │                    │ Jobs        │    │ Engine       │
└─────────────┘                    └─────────────┘    └──────────────┘
```

## 🚀 Cách chạy

### Yêu cầu hệ thống
- Docker & Docker Compose
- RAM tối thiểu: 8GB (khuyến nghị 16GB)
- Ổ đĩa trống: 5GB

### Bước 1: Clone repo
```bash
git clone <repository-url>
cd final-project
```

### Bước 2: Khởi động hệ thống

**Khởi động cơ bản (khuyến nghị):**
```cmd
start_basic.bat
```

**Khởi động đầy đủ:**
```cmd
start_pipeline.bat
```

**Kiểm tra trạng thái:**
```cmd
check_status.bat
```

**Hoặc sử dụng Docker Compose trực tiếp:**
```bash
# Khởi động services cơ bản
docker-compose up -d postgres redis zookeeper kafka
timeout /t 20 /nobreak
docker exec kafka kafka-topics --create --topic user_events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
docker-compose up -d web-app

# Khởi động Spark (tùy chọn)
docker-compose up -d spark-master spark-worker
```

### Bước 3: Truy cập ứng dụng

- **Web App**: http://localhost:5000
- **Spark Master UI**: http://localhost:8080
- **Kafka Manager**: http://localhost:9092

## 📊 Data Flow

1. **User Interaction**: User tương tác với website (click, search, view)
2. **Event Streaming**: Events được gửi đến Kafka real-time
3. **Event Processing**: Kafka consumer xử lý và lưu vào database
4. **Batch Analytics**: Spark job chạy định kỳ để phân tích dữ liệu
5. **ML Model Training**: Train mô hình Collaborative Filtering
6. **Recommendation Generation**: Tạo gợi ý và cache vào Redis
7. **Real-time Updates**: Cập nhật gợi ý khi có tương tác mới

## 🔧 Components

### Web Application (`/web-app`)
- **Framework**: Flask với SQLAlchemy
- **Frontend**: Bootstrap 5
- **Features**: User auth, product catalog, search, recommendations
- **Tracking**: JavaScript tracking cho user events

### Kafka Processing (`/kafka-config`)
- **Consumer**: Xử lý events từ Kafka
- **Database**: Lưu raw events và processed data
- **Redis**: Cache user profiles và statistics

### Spark Analytics (`/spark-processing`)
- **Batch Job**: `user_behavior_analyzer.py` - Phân tích hành vi định kỳ
- **Streaming Job**: `realtime_recommendation.py` - Cập nhật real-time
- **ML Models**: ALS Collaborative Filtering

### Recommendation Engine (`/recommendation-engine`)
- **Hybrid Approach**: Kết hợp 4 phương pháp
- **API**: RESTful API cho web app
- **Caching**: Redis cache cho performance

## 🎛️ Configuration

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://admin:password123@postgres:5432/ecommerce_db

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092

# Redis
REDIS_URL=redis://redis:6379
```

### Spark Configuration
```python
# Spark Session config
.config("spark.sql.adaptive.enabled", "true")
.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
```

## 📈 Monitoring & Logs

### Xem logs của các services
```bash
# Web application
docker-compose logs -f web-app

# Kafka processor
docker-compose logs -f kafka-processor

# Spark jobs
docker-compose logs -f batch-processor

# Tất cả services
docker-compose logs -f
```

### Spark UI
- Truy cập http://localhost:8080 để xem Spark cluster
- Monitor job execution và resource usage

## 🧪 Testing

### Tạo dữ liệu test
1. Đăng ký tài khoản mới trên web
2. Duyệt qua các sản phẩm khác nhau
3. Thực hiện tìm kiếm
4. Click vào các sản phẩm
5. Kiểm tra gợi ý tại `/recommendations`

### Kiểm tra pipeline
```bash
# Kiểm tra Kafka topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Kiểm tra messages trong topic
docker exec kafka kafka-console-consumer --topic user_events --bootstrap-server localhost:9092 --from-beginning

# Kiểm tra Redis data
docker exec redis redis-cli keys "*"
```

## 🛠️ Development

### Thêm sản phẩm mới
```sql
INSERT INTO product (name, description, price, category, stock) 
VALUES ('Tên sản phẩm', 'Mô tả', 1000000, 'Category', 100);
```

### Custom recommendation logic
Chỉnh sửa file `recommendation-engine/recommendation_api.py`:
```python
def combine_recommendations(self, cf_recs, content_recs, popularity_recs, behavior_recs, num_recommendations):
    # Thay đổi trọng số
    weights = {
        'cf': 0.5,        # Tăng trọng số CF
        'content': 0.3,
        'popularity': 0.15,
        'behavior': 0.05
    }
```

## 🐛 Troubleshooting

### Lỗi thường gặp

**1. Services không khởi động được**
```bash
# Kiểm tra ports có bị chiếm không
netstat -tulpn | grep :5000
netstat -tulpn | grep :9092

# Restart services
docker-compose restart
```

**2. Kafka connection error**
```bash
# Kiểm tra Kafka status
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Recreate topics nếu cần
docker exec kafka kafka-topics --delete --topic user_events --bootstrap-server localhost:9092
```

**3. Spark job fails**
```bash
# Kiểm tra logs
docker-compose logs spark-master
docker-compose logs spark-worker

# Restart Spark cluster
docker-compose restart spark-master spark-worker
```

**4. Database connection issues**
```bash
# Kiểm tra PostgreSQL
docker exec postgres psql -U admin -d ecommerce_db -c "\\dt"

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

## 📚 Technologies Used

- **Backend**: Python, Flask, SQLAlchemy
- **Database**: PostgreSQL, Redis
- **Streaming**: Apache Kafka
- **Analytics**: Apache Spark, PySpark
- **Machine Learning**: Spark MLlib (ALS), Scikit-learn
- **Frontend**: HTML, Bootstrap 5, JavaScript
- **Containerization**: Docker, Docker Compose

## 🔮 Future Enhancements

- [ ] A/B testing cho recommendation algorithms
- [ ] Deep Learning models (Neural Collaborative Filtering)
- [ ] Real-time dashboard với metrics
- [ ] Mobile app integration
- [ ] Advanced analytics (cohort analysis, churn prediction)
- [ ] Multi-armed bandit cho recommendation optimization

## 👥 Team

Dự án được phát triển cho môn học Big Data - HUIT.

## 📄 License

MIT License - See LICENSE file for details.

---

**📞 Support**: Nếu gặp vấn đề, tạo issue trên GitHub hoặc liên hệ team phát triển.