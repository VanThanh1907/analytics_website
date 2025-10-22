#!/bin/bash

# Script để chạy toàn bộ pipeline

echo "🚀 Khởi động E-commerce Analytics Pipeline..."

# 1. Khởi động các services cơ bản
echo "📦 Khởi động Docker services..."
docker-compose up -d zookeeper kafka postgres redis

# Đợi services khởi động
echo "⏳ Đợi services khởi động..."
sleep 30

# 2. Tạo Kafka topics
echo "📢 Tạo Kafka topics..."
docker exec kafka kafka-topics --create --topic user_events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
docker exec kafka kafka-topics --create --topic spark_processing --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

# 3. Khởi động web application
echo "🌐 Khởi động web application..."
docker-compose up -d web-app

# 4. Khởi động Spark cluster
echo "⚡ Khởi động Spark cluster..."
docker-compose up -d spark-master spark-worker

# 5. Khởi động Kafka event processor
echo "🔄 Khởi động Kafka event processor..."
docker-compose up -d kafka-processor

# 6. Khởi động batch processing job (chạy mỗi giờ)
echo "📊 Khởi động batch processing..."
docker-compose up -d batch-processor

# 7. Khởi động real-time processing
echo "⚡ Khởi động real-time processing..."
docker-compose up -d realtime-processor

echo "✅ Tất cả services đã được khởi động!"
echo ""
echo "🔗 URLs quan trọng:"
echo "  - Web App: http://localhost:5000"
echo "  - Spark Master UI: http://localhost:8080"
echo "  - Kafka Topics: http://localhost:9092"
echo ""
echo "📝 Logs:"
echo "  docker-compose logs -f [service-name]"
echo ""
echo "🛑 Để dừng tất cả:"
echo "  docker-compose down"