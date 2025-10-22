@echo off
echo ========================================
echo   BIG DATA RECOMMENDATION SYSTEM
echo ========================================
echo.
echo Starting services...
echo.

echo [1/2] Starting Recommendation API Server (Port 5002)...
start "API Server" cmd /k "cd /d "%~dp0recommendation-engine" && python -c "from api_server import app; app.run(debug=True, port=5002, host='0.0.0.0')""

echo Waiting for API server to start...
timeout /t 3 /nobreak > nul

echo [2/2] Starting Web Application (Port 5000)...
start "Web App" cmd /k "cd /d "%~dp0web-app" && python app.py"

echo.
echo ========================================
echo   SERVICES STARTED SUCCESSFULLY!
echo ========================================
echo.
echo Web Application: http://localhost:5000
echo API Server:      http://localhost:5002
echo.
echo Login with: testuser / 123456
echo.
echo Press any key to open web browser...
pause > nul

start http://localhost:5000

echo.
echo Both services are running in separate windows.
echo Close those windows to stop the services.
echo.
pause