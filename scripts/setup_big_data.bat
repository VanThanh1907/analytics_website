@echo off
echo ========================================
echo   BIG DATA INFRASTRUCTURE SETUP
echo ========================================
echo.
echo Setting up distributed storage and processing...
echo.

REM Ensure Docker is running
echo [1/6] Checking Docker status...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed or running!
    echo Please install Docker Desktop and try again.
    pause
    exit /b 1
)
echo ✅ Docker is ready

REM Create Docker network
echo [2/6] Creating Docker network...
docker network create bigdata_network 2>nul
echo ✅ Network created/exists

REM Start HDFS Cluster
echo [3/6] Starting HDFS Cluster (Distributed Storage)...
cd "%~dp0..\big-data-infrastructure\hdfs-cluster"
docker-compose -f docker-compose-hdfs.yml up -d
if errorlevel 1 (
    echo ❌ Failed to start HDFS cluster
    pause
    exit /b 1
)
echo ✅ HDFS cluster started

REM Wait for HDFS to be ready
echo [4/6] Waiting for HDFS NameNode to be ready...
timeout /t 30 /nobreak > nul
echo ✅ HDFS should be ready

REM Start Spark Cluster  
echo [5/6] Starting Spark Cluster (Big Data Processing)...
cd "..\spark-cluster"
docker-compose -f docker-compose-spark.yml up -d
if errorlevel 1 (
    echo ❌ Failed to start Spark cluster
    pause
    exit /b 1
)
echo ✅ Spark cluster started

REM Install Python dependencies
echo [6/6] Installing Python dependencies...
cd "%~dp0..\dashboard"
pip install -r requirements.txt --quiet
cd "%~dp0"

echo.
echo ========================================
echo   BIG DATA INFRASTRUCTURE READY!
echo ========================================
echo.
echo 🗄️  HDFS NameNode UI:  http://localhost:9870
echo ⚡ Spark Master UI:   http://localhost:8080
echo 📊 DataNode 1:        http://localhost:9864
echo 📊 DataNode 2:        http://localhost:9865
echo.
echo ✅ Distributed storage (HDFS) is running
echo ✅ Big data processing (Spark) is running
echo ✅ Ready for analytics pipeline
echo.
pause