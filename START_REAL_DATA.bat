@echo off
echo ========================================
echo   REAL DATA DEMO - 100%% Du lieu that
echo ========================================
echo.

REM Kiem tra Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python khong duoc cai dat!
    pause
    exit /b 1
)

echo [1/3] Starting Recommendation API Server (100%% REAL DATA)...
start "Recommendation API (REAL DATA)" cmd /k "cd recommendation-engine && python api_server_real.py"
timeout /t 3 /nobreak >nul

echo [2/3] Starting Web Application (SQLite Database)...
start "Web App (Real Data)" cmd /k "cd web-app && python app.py"
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   TAT CA SERVICES DA KHOI DONG
echo ========================================
echo.
echo  Web App:           http://localhost:5000
echo  Recommendation API: http://localhost:5001
echo.
echo  DATA SOURCE: 100%% SQLite Database
echo  - Khong co mock data
echo  - Khong co random fallback
echo  - Chi su dung du lieu tuong tac thuc te
echo.
echo [Chi dan su dung]
echo 1. Truy cap http://localhost:5000
echo 2. Dang nhap voi user co san (test_user/password123)
echo 3. Click vao cac san pham
echo 4. Xem goi y tu du lieu THAT o /recommendations
echo.
echo Nhan phim bat ky de dong tat ca services...
pause >nul

echo.
echo Dang dong tat ca services...
taskkill /FI "WINDOWTITLE eq Recommendation API (REAL DATA)*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Web App (Real Data)*" /T /F >nul 2>&1

echo.
echo Tat ca services da duoc dong.
echo.
pause
