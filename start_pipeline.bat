@echo off
chcp 65001 > nul
REM Script to start the complete pipeline on Windows

echo Starting E-commerce Analytics Pipeline...

REM 1. Start basic services
echo Starting Docker services...
docker-compose up -d zookeeper kafka postgres redis

REM Wait for services to start
echo Waiting for services to start...
timeout /t 30 /nobreak > nul

REM 2. Create Kafka topics
echo Creating Kafka topics...
docker exec kafka kafka-topics --create --topic user_events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists
docker exec kafka kafka-topics --create --topic spark_processing --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

REM 3. Start web application
echo Starting web application...
docker-compose up -d web-app

REM 4. Start Spark cluster
echo Starting Spark cluster...
docker-compose up -d spark-master spark-worker

echo Services have been started successfully!
echo.
echo Important URLs:
echo   - Web App: http://localhost:5000
echo   - Spark Master UI: http://localhost:8080
echo   - Kafka Topics: http://localhost:9092
echo.
echo Logs:
echo   docker-compose logs -f [service-name]
echo.
echo To stop all services:
echo   docker-compose down
echo.
pause