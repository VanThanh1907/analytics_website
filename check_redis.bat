@echo off
chcp 65001 > nul

echo ===================================
echo    REDIS DATA INSPECTOR
echo ===================================
echo.

echo Checking Redis data...
echo.

echo === User Recommendations ===
docker exec redis_cache redis-cli keys "*recommendations*"
echo.

echo === User Preferences ===  
docker exec redis_cache redis-cli keys "*user_preferences*"
echo.

echo === User Profiles ===
docker exec redis_cache redis-cli keys "*user_profile*"
echo.

echo === Product Stats ===
docker exec redis_cache redis-cli keys "*product_stats*"
echo.

echo === User Recent Views ===
docker exec redis_cache redis-cli keys "*recent_views*"
echo.

echo === Sample User 1 Recommendations ===
docker exec redis_cache redis-cli get "recommendations:user:1"
echo.

echo === Sample User 1 Preferences ===
docker exec redis_cache redis-cli hgetall "user_preferences:1"
echo.

echo === Trending Products ===
docker exec redis_cache redis-cli get "trending_products"
echo.

echo ===================================
pause