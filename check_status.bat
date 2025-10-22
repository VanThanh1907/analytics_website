@echo off
chcp 65001 > nul

echo Checking E-commerce Pipeline Status...
echo.

echo === Docker Services Status ===
docker-compose ps


echo.
echo === Service URLs ===
echo Web App: http://localhost:5000
echo Postgres: localhost:5432
echo Redis: localhost:6379
echo Kafka: localhost:9092

echo.
echo === Quick Health Checks ===

echo Checking Web App...
curl -s -o nul -w "Web App Status: %%{http_code}\n" http://localhost:5000 2>nul || echo Web App: Not responding

echo Checking Postgres...
docker exec postgres_db pg_isready -U admin > nul 2>&1 && echo Postgres: Ready || echo Postgres: Not ready

echo Checking Redis...
docker exec redis_cache redis-cli ping > nul 2>&1 && echo Redis: Ready || echo Redis: Not ready

echo Checking Kafka...
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > nul 2>&1 && echo Kafka: Ready || echo Kafka: Not ready

echo.
echo To start Spark cluster:
echo   docker-compose up -d spark-master spark-worker
echo.
echo To view logs:
echo   docker-compose logs -f [service-name]
echo.
pause