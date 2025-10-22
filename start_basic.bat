@echo off
chcp 65001 > nul

echo Starting basic E-commerce services...

echo Step 1: Starting PostgreSQL and Redis...
docker-compose up -d postgres redis

echo Step 2: Starting Kafka infrastructure...
docker-compose up -d zookeeper
timeout /t 10 /nobreak > nul
docker-compose up -d kafka

echo Step 3: Waiting for Kafka to be ready...
timeout /t 20 /nobreak > nul

echo Step 4: Creating Kafka topics...
docker exec kafka kafka-topics --create --topic user_events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
docker exec kafka kafka-topics --create --topic spark_processing --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

echo Step 5: Starting web application...
docker-compose up -d web-app

echo.
echo Basic services started successfully!
echo Web App: http://localhost:5000
echo.
echo To start Spark cluster later, run:
echo   docker-compose up -d spark-master spark-worker
echo.
echo To see logs:
echo   docker-compose logs -f web-app
echo.
pause