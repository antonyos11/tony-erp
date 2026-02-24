@echo off
chcp 65001 >nul 2>&1

echo ================================================================================
echo فحص Docker في النظام
echo ================================================================================
echo.

:: التحقق من Docker
echo جاري فحص Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo فشل: Docker غير مثبت أو غير يعمل
    echo.
    echo حلول مقترحة:
    echo    1. تحميل Docker Desktop من: https://docker.com/products/docker-desktop
    echo    2. تثبيت Docker Desktop وإعادة تشغيل الكمبيوتر
    echo    3. تأكد من تشغيل Docker Desktop قبل المحاولة مرة أخرى
    echo    4. في Windows، تحتاج WSL 2 أو Hyper-V
    echo.
    pause
    exit /b 1
) else (
    echo Docker متوفر:
    docker --version
)

echo.
echo جاري فحص Docker Compose...
docker compose version >nul 2>&1
if errorlevel 1 (
    echo فشل: Docker Compose غير متاح
    echo ملاحظة: عادة يأتي مع Docker Desktop الحديث
) else (
    echo Docker Compose متوفر:
    docker compose version
)

echo.
echo جاري فحص ملف docker-compose.yml...
if exist docker-compose.yml (
    echo ملف docker-compose.yml موجود
) else (
    echo فشل: ملف docker-compose.yml غير موجود
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo بدء تشغيل خدمات Docker
echo ================================================================================
echo.

echo جاري إيقاف الحاويات السابقة إن وجدت...
docker compose down

echo.
echo جاري بناء وتشغيل الحاويات...
docker compose up -d --build

echo.
echo انتظار بدء الخدمات...
timeout /t 30 >nul

echo.
echo جاري فحص حالة الحاويات...
docker compose ps

echo.
echo ================================================================================
echo تشغيل فحص النظام
echo ================================================================================
echo.

echo جاري تشغيل فحص النظام داخل حاوية الويب...
docker compose exec web python manage.py system_self_check --fix

echo.
echo ================================================================================
echo معلومات مفيدة
echo ================================================================================
echo.
echo النظام متاح على: http://127.0.0.1:8000
echo لوحة الإدارة: http://127.0.0.1:8000/admin/
echo وثائق API: http://127.0.0.1:8000/api/docs/
echo Flower (مراقب المهام): http://127.0.0.1:5555
echo فحص الصحة: http://127.0.0.1:8000/health/ready/
echo.
echo تنبيه: إذا كانت هذه أول مرة، غيّر كلمة المرور الافتراضية فوراً
echo استخدم: python manage.py changepassword superadmin
echo.

echo للاطلاع على سجلات النظام:
echo docker compose logs -f web

echo.
echo لإيقاف النظام:
echo docker compose down

echo.
pause