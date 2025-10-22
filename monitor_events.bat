@echo off
chcp 65001 > nul

echo ===================================
echo    KAFKA EVENTS MONITORING
echo ===================================
echo.

echo Starting monitoring terminals...
echo.

echo 1. User Events Monitor (Terminal 1)
echo Press CTRL+C to stop
echo.
start "User Events" cmd /k "docker exec kafka kafka-console-consumer --topic user_events --bootstrap-server localhost:9092 --from-beginning"

timeout /t 2 /nobreak > nul

echo 2. Processed Events Monitor (Terminal 2)  
echo Press CTRL+C to stop
echo.
start "Processed Events" cmd /k "docker exec kafka kafka-console-consumer --topic spark_processing --bootstrap-server localhost:9092 --from-beginning"

timeout /t 2 /nobreak > nul

echo 3. Kafka Processor Logs (Terminal 3)
echo Press CTRL+C to stop
echo.
start "Kafka Processor" cmd /k "docker-compose logs -f kafka-processor"

echo.
echo ✅ Monitoring terminals opened!
echo.
echo Now browse the website at: http://localhost:5000
echo - Register different users
echo - Browse different product categories  
echo - Search for products
echo - Click on products
echo.
echo Watch the real-time events in the opened terminals!
echo.
pause