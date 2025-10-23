@echo off
echo ========================================
echo   BIG DATA E-COMMERCE ANALYTICS SYSTEM
echo ========================================
echo.
echo 🎯 Features: Distributed Storage + Big Data Processing + ML + Real-time Dashboard
echo.

REM Check if big data infrastructure is running
echo [1/8] Checking Big Data Infrastructure...
docker ps --format "table {{.Names}}" | findstr namenode >nul 2>&1
if errorlevel 1 (
    echo 🔧 Big Data infrastructure not running. Starting now...
    call "%~dp0scripts\setup_big_data.bat"
) else (
    echo ✅ Big Data infrastructure is already running
)

echo [2/8] Starting Kafka Event Processor...
REM Note: Add Kafka startup here if needed

echo [3/8] Starting Recommendation API Server (Port 5002)...
start "API Server" cmd /k "cd /d "%~dp0recommendation-engine" && python -c "from api_server import app; app.run(debug=True, port=5002, host='0.0.0.0')""

echo [4/8] Waiting for API server to start...
timeout /t 3 /nobreak > nul

echo [5/8] Starting Big Data Analytics Dashboard (Port 8050)...
start "Analytics Dashboard" cmd /k "cd /d "%~dp0dashboard" && python analytics_dashboard.py"

echo [6/8] Starting Web Application (Port 5000)...
start "Web App" cmd /k "cd /d "%~dp0web-app" && python app.py"

echo [7/8] Preparing analytics pipeline...
timeout /t 5 /nobreak > nul

echo [8/8] Running initial data migration and ML analysis...
start "Analytics Pipeline" cmd /k "cd /d "%~dp0analytics-engine\spark-jobs" && python user_segmentation.py"

echo.
echo ========================================
echo   BIG DATA SYSTEM STARTED SUCCESSFULLY!
echo ========================================
echo.
echo 🌐 E-commerce Web App:     http://localhost:5000
echo 🤖 Recommendation API:     http://localhost:5002  
echo 📊 Analytics Dashboard:    http://localhost:8050
echo 🗄️  HDFS NameNode UI:       http://localhost:9870
echo ⚡ Spark Master UI:        http://localhost:8080
echo.
echo 👤 Login credentials: testuser / 123456
echo.
echo 🎯 DEMO FEATURES:
echo   ✅ Distributed Storage (HDFS)
echo   ✅ Big Data Processing (Spark)
echo   ✅ Machine Learning (Clustering + Collaborative Filtering)
echo   ✅ Real-time Analytics Dashboard
echo   ✅ Instant Recommendation System
echo.
echo Press any key to open main dashboard...
pause > nul

start http://localhost:8050

echo.
echo 📋 All services are running in separate windows.
echo 🛑 Close those windows to stop the services.
echo 🔄 Check dashboard for real-time analytics!
echo.
pause