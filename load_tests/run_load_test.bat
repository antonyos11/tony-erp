@echo off
REM Load Testing Script for Tony ERP (Windows)
REM سكريبت اختبار الأداء لنظام Tony ERP

echo =========================================
echo Tony ERP Load Testing
echo =========================================
echo.

REM Check if Locust is installed
python -c "import locust" 2>nul
if errorlevel 1 (
    echo Locust غير مثبت. جاري التثبيت...
    pip install locust
)

REM Default values
set HOST=http://localhost:8000
set USERS=50
set SPAWN_RATE=5
set RUN_TIME=5m

echo اختر نوع الاختبار:
echo 1^) اختبار خفيف ^(10 users, 2 min^)
echo 2^) اختبار متوسط ^(50 users, 5 min^)
echo 3^) اختبار ثقيل ^(100 users, 10 min^)
echo 4^) اختبار شديد ^(200 users, 15 min^)
echo 5^) مخصص
echo.

set /p choice="اختر (1-5): "

if "%choice%"=="1" (
    set USERS=10
    set SPAWN_RATE=2
    set RUN_TIME=2m
) else if "%choice%"=="2" (
    set USERS=50
    set SPAWN_RATE=5
    set RUN_TIME=5m
) else if "%choice%"=="3" (
    set USERS=100
    set SPAWN_RATE=10
    set RUN_TIME=10m
) else if "%choice%"=="4" (
    set USERS=200
    set SPAWN_RATE=10
    set RUN_TIME=15m
) else if "%choice%"=="5" (
    set /p USERS="عدد المستخدمين: "
    set /p SPAWN_RATE="معدل الإضافة (users/sec): "
    set /p RUN_TIME="مدة الاختبار (مثال: 5m): "
) else (
    echo اختيار غير صحيح. استخدام الإعدادات الافتراضية.
)

echo.
echo بدء الاختبار...
echo.

REM Create results directory
if not exist "load_tests\results" mkdir "load_tests\results"

REM Get timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do (set mytime=%%a%%b)
set timestamp=%mydate%_%mytime%

REM Run Locust
locust ^
    -f load_tests\locustfile.py ^
    --host=%HOST% ^
    --users=%USERS% ^
    --spawn-rate=%SPAWN_RATE% ^
    --run-time=%RUN_TIME% ^
    --headless ^
    --html=load_tests\results\report_%timestamp%.html ^
    --csv=load_tests\results\results_%timestamp% ^
    --loglevel=INFO

echo.
echo اكتمل الاختبار!
echo التقارير موجودة في: load_tests\results\
echo.
pause
