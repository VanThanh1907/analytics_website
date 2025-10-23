@echo off
chcp 65001 >nul
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                                                                   ║
echo ║          🚀 DEMO - HỆ THỐNG GỢI Ý SẢN PHẨM REAL-TIME            ║
echo ║                    100%% Dữ Liệu Thật                             ║
echo ║                                                                   ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.

REM Kiểm tra Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Lỗi: Python chưa được cài đặt!
    pause
    exit /b 1
)

echo [1/2] 🤖 Đang khởi động Recommendation API Server...
start "API Server (Port 5001)" cmd /k "cd recommendation-engine && python api_server_real.py"
timeout /t 3 /nobreak >nul
echo       ✅ Recommendation API: http://localhost:5001
echo.

echo [2/2] 🌐 Đang khởi động Web Application...
start "Web App (Port 5000)" cmd /k "cd web-app && python app.py"
timeout /t 5 /nobreak >nul
echo       ✅ Web Application: http://localhost:5000
echo.

echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                     ✅ HỆ THỐNG ĐÃ SẴN SÀNG!                      ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.
echo  📍 TRUY CẬP:
echo     🌐 Web:  http://localhost:5000
echo     🔧 API:  http://localhost:5001
echo.
echo  👤 TÀI KHOẢN DEMO:
echo     Username: vanthanh   (137 interactions)
echo     Username: testuser   (286 interactions)
echo     Password: [password của bạn]
echo.
echo  🎯 DEMO SCRIPT:
echo     1. Mở: http://localhost:5000
echo     2. Login với tài khoản trên
echo     3. Click vào 3-5 sản phẩm bất kỳ
echo     4. Vào: http://localhost:5000/recommendations
echo     5. ✨ Thấy gợi ý từ dữ liệu THẬT!
echo     6. Click sản phẩm category khác
echo     7. Refresh /recommendations → Gợi ý thay đổi NGAY!
echo.
echo  📊 DATA:
echo     ✅ SQLite Database: web-app\instance\ecommerce.db
echo     ✅ 1060+ real interactions
echo     ✅ 104 products, 9 categories
echo     ✅ Instant category switch (30 min)
echo.
echo  🛑 DỪNG HỆ THỐNG:
echo     Nhấn phím bất kỳ để dừng tất cả services...
echo.

REM Tự động mở browser
timeout /t 2 /nobreak >nul
start http://localhost:5000

pause

echo.
echo 🛑 Đang dừng tất cả services...
taskkill /FI "WINDOWTITLE eq API Server*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Web App*" /T /F >nul 2>&1
echo ✅ Đã dừng tất cả services
echo.
pause
