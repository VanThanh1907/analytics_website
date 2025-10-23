@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║     🚀 KHỞI ĐỘNG TOÀN BỘ HỆ THỐNG - 4 SERVICES           ║
echo ║     100%% Dữ Liệu Thật - Real-time Recommendations        ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM ============================================
REM Kiểm tra Python
REM ============================================
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ LỖI: Python chưa được cài đặt!
    echo.
    echo 💡 Hãy cài đặt Python từ: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python: OK
python --version
echo.

REM ============================================
REM Kiểm tra Docker (optional - cho Kafka/Redis)
REM ============================================
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Docker không được tìm thấy
    echo    Kafka và Redis sẽ không khởi động
    echo    Hệ thống vẫn hoạt động với SQLite database
    set USE_DOCKER=0
) else (
    echo ✅ Docker: OK
    docker --version
    set USE_DOCKER=1
)
echo.

REM ============================================
REM Cài đặt dependencies
REM ============================================
echo ╔════════════════════════════════════════════════════════════╗
echo ║  📦 BƯỚC 1/4: Cài đặt Python Dependencies                  ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

if not exist "venv" (
    echo 🔧 Tạo Python virtual environment...
    python -m venv venv
    echo ✅ Virtual environment đã tạo
)

echo 🔧 Kích hoạt virtual environment...
call venv\Scripts\activate.bat

echo 🔧 Cài đặt dependencies cho Web App...
cd web-app
pip install -r requirements.txt -q
cd ..

echo 🔧 Cài đặt dependencies cho Recommendation Engine...
cd recommendation-engine
pip install -r requirements.txt -q
cd ..

echo ✅ Dependencies đã cài đặt xong
echo.

REM ============================================
REM Khởi động Kafka và Redis (nếu có Docker)
REM ============================================
if "%USE_DOCKER%"=="1" (
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  🐳 BƯỚC 2/4: Khởi động Kafka ^& Redis                      ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    
    echo 🔧 Kiểm tra Kafka container...
    docker ps -a | findstr kafka >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo ♻️  Kafka container đã tồn tại, khởi động lại...
        docker start kafka >nul 2>&1
    ) else (
        echo 🚀 Khởi động Kafka lần đầu...
        docker-compose up -d kafka 2>nul
    )
    
    echo 🔧 Kiểm tra Redis container...
    docker ps -a | findstr redis >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo ♻️  Redis container đã tồn tại, khởi động lại...
        docker start redis_cache >nul 2>&1
    ) else (
        echo 🚀 Khởi động Redis lần đầu...
        docker-compose up -d redis 2>nul
    )
    
    echo ⏳ Đợi Kafka và Redis khởi động... (5s)
    timeout /t 5 /nobreak >nul
    echo ✅ Kafka và Redis đã sẵn sàng
    echo.
) else (
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║  ⚠️  BƯỚC 2/4: Bỏ qua Kafka ^& Redis (không có Docker)     ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo ℹ️  Hệ thống sẽ hoạt động chỉ với SQLite database
    echo.
)

REM ============================================
REM Khởi động Recommendation API
REM ============================================
echo ╔════════════════════════════════════════════════════════════╗
echo ║  🤖 BƯỚC 3/4: Khởi động Recommendation API Server         ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

start "🤖 Recommendation API (Real Data)" cmd /k "call venv\Scripts\activate.bat && cd recommendation-engine && python api_server_real.py"

echo ⏳ Đợi API server khởi động... (3s)
timeout /t 3 /nobreak >nul
echo ✅ Recommendation API đã khởi động
echo.

REM ============================================
REM Khởi động Web Application
REM ============================================
echo ╔════════════════════════════════════════════════════════════╗
echo ║  🌐 BƯỚC 4/4: Khởi động Web Application                   ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

start "🌐 Web App (SQLite Real Data)" cmd /k "call venv\Scripts\activate.bat && cd web-app && python app.py"

echo ⏳ Đợi Web App khởi động... (5s)
timeout /t 5 /nobreak >nul
echo ✅ Web Application đã khởi động
echo.

REM ============================================
REM Hiển thị thông tin
REM ============================================
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              ✅ TẤT CẢ SERVICES ĐÃ KHỞI ĐỘNG              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo  📍 DANH SÁCH SERVICES:
echo  ─────────────────────────────────────────────────────────────
if "%USE_DOCKER%"=="1" (
    echo  1️⃣  Kafka:              localhost:9092
    echo  2️⃣  Redis:              localhost:6379
)
echo  3️⃣  Recommendation API:  http://localhost:5001
echo  4️⃣  Web Application:     http://localhost:5000
echo.
echo  📊 DATA SOURCE:
echo  ─────────────────────────────────────────────────────────────
echo     ✅ 100%% SQLite Database (web-app\instance\ecommerce.db)
echo     ✅ Real-time interactions tracking
echo     ✅ Instant category switch
echo     ❌ No mock data, no random fallback
echo.
echo  🎯 HƯỚNG DẪN SỬ DỤNG:
echo  ─────────────────────────────────────────────────────────────
echo     1. Mở trình duyệt: http://localhost:5000
echo     2. Đăng nhập với tài khoản có sẵn:
echo        - Username: vanthanh (hoặc testuser)
echo        - Password: [password của bạn]
echo     3. Click vào các sản phẩm để tạo interactions
echo     4. Xem gợi ý: http://localhost:5000/recommendations
echo     5. Click category khác → Gợi ý thay đổi NGAY!
echo.
echo  🔧 TEST & DEBUG:
echo  ─────────────────────────────────────────────────────────────
echo     - Kiểm tra database:  python check_interactions.py
echo     - Test recommendations: python test_real_recommendations.py
echo     - API health check:   curl http://localhost:5001/health
echo.
echo  ⚙️  QUẢN LÝ SERVICES:
echo  ─────────────────────────────────────────────────────────────
echo     - Recommendation API: Cửa sổ "🤖 Recommendation API"
echo     - Web App:           Cửa sổ "🌐 Web App"
if "%USE_DOCKER%"=="1" (
    echo     - Kafka/Redis:       docker ps
    echo     - Stop Kafka/Redis:  docker-compose down
)
echo.

REM ============================================
REM Tự động mở browser
REM ============================================
echo ⏳ Tự động mở trình duyệt trong 3 giây...
timeout /t 3 /nobreak >nul
start http://localhost:5000

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    🎉 HỆ THỐNG ĐÃ SẴN SÀNG!               ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo  💡 Để DỪNG tất cả services:
echo     - Nhấn phím bất kỳ trong cửa sổ này
echo     - Hoặc đóng các cửa sổ terminal
if "%USE_DOCKER%"=="1" (
    echo     - Chạy: docker-compose down
)
echo.

pause

REM ============================================
REM Dọn dẹp khi thoát
REM ============================================
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              🛑 ĐANG DỪNG TẤT CẢ SERVICES...              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

echo 🔧 Dừng Recommendation API...
taskkill /FI "WINDOWTITLE eq 🤖 Recommendation API*" /T /F >nul 2>&1

echo 🔧 Dừng Web App...
taskkill /FI "WINDOWTITLE eq 🌐 Web App*" /T /F >nul 2>&1

if "%USE_DOCKER%"=="1" (
    echo 🔧 Dừng Kafka và Redis...
    docker stop kafka redis_cache >nul 2>&1
)

echo.
echo ✅ Tất cả services đã dừng
echo.
echo 👋 Cảm ơn bạn đã sử dụng!
echo.
pause
