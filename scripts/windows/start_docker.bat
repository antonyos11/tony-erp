@echo off
chcp 65001 >nul 2>&1
title Tony ERP - تشغيل النظام بـ Docker

echo.
echo ================================================================================
echo Tony ERP - تشغيل النظام بـ Docker
echo ================================================================================
echo.

:: التحقق من وجود Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo خطأ: Docker غير مثبت أو غير متاح
    echo يرجى تثبيت Docker Desktop من: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: التحقق من وجود Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    echo خطأ: Docker Compose غير متاح
    echo يرجى تثبيت Docker Compose أو استخدام إصدار حديث من Docker Desktop
    pause
    exit /b 1
)

echo Docker متوفر:
docker --version
docker compose version

:: التحقق من وجود ملف .env
if not exist ".env" (
    echo إنشاء ملف الإعدادات...
    if exist ".env.example" (
        copy .env.example .env >nul
    echo تم إنشاء ملف .env من .env.example
    ) else (
    echo خطأ: لم يتم العثور على .env.example
        pause
        exit /b 1
    )
)

:: إيقاف الخدمات المشتغلة (إن وجدت)
echo إيقاف الخدمات السابقة...
docker compose down >nul 2>&1

:: بناء وتشغيل الخدمات
echo.
echo بناء وتشغيل خدمات Docker...
echo هذا قد يستغرق عدة دقائق في المرة الأولى...
echo.

docker compose up --build -d
if errorlevel 1 (
    echo خطأ في تشغيل Docker Compose
    echo تحقق من ملف docker-compose.yml والمسارات
    pause
    exit /b 1
)

:: انتظار حتى يصبح النظام جاهزاً
echo انتظار بدء الخدمات...
timeout /t 30 /nobreak >nul

:: فحص حالة الخدمات
echo فحص حالة الخدمات...
docker compose ps

:: انتظار حتى يصبح النظام متاحاً
echo فحص توفر النظام...
set /a retries=0
:check_health
timeout /t 5 /nobreak >nul
curl -s http://127.0.0.1:8000/health/ready/ >nul 2>&1
if errorlevel 1 (
    set /a retries+=1
    if %retries% lss 12 (
        echo انتظار... (%retries%/12^)
        goto check_health
    ) else (
    echo تحذير: النظام قد لا يكون جاهزاً بعد
    echo تحقق من السجلات: docker compose logs web
    )
) else (
    echo النظام متاح ويعمل
)

echo.
echo ================================================================================
echo تم تشغيل Tony ERP بنجاح باستخدام Docker!
echo ================================================================================
echo.
echo النظام متاح على: http://127.0.0.1:8000
echo.
echo ملاحظة مهمة: تأكد من تغيير كلمة المرور الافتراضية فوراً
echo من لوحة الإدارة: http://127.0.0.1:8000/admin/password_change/
echo.
echo روابط مفيدة:
echo    - لوحة الإدارة: http://127.0.0.1:8000/admin/
echo    - واجهة API: http://127.0.0.1:8000/api/docs/
echo    - مراقب Flower: http://127.0.0.1:5555
echo    - حالة النظام: http://127.0.0.1:8000/health/ready/
echo.
echo أوامر مفيدة:
echo    - عرض السجلات: docker compose logs -f web
echo    - إيقاف النظام: docker compose down
echo    - إعادة تشغيل: docker compose restart
echo    - فحص الحاويات: docker compose ps
echo.
echo ================================================================================

:: فتح المتصفح
echo فتح المتصفح...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000

echo.
echo النظام يعمل في الخلفية. لإيقافه، شغّل: docker compose down
echo لعرض السجلات المباشرة، شغّل: docker compose logs -f web
echo.
pause