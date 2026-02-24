@echo off
chcp 65001 >nul 2>&1
title تثبيت Tony ERP - نظام إدارة الأعمال الشامل

echo.
echo ================================================================================
echo مرحباً بك في Tony ERP - نظام إدارة الأعمال الشامل
echo ================================================================================
echo.
echo هذا المعالج سيقوم بإعداد النظام تلقائياً:
echo   - إنشاء البيئة الافتراضية
echo   - تثبيت المكتبات المطلوبة  
echo   - إعداد قاعدة البيانات
echo   - تحميل البيانات التجريبية
echo   - فحص النظام وإصلاح المشاكل
echo   - تشغيل الخادم وفتح المتصفح
echo.
echo ================================================================================

:: التحقق من وجود Python
python --version >nul 2>&1
if errorlevel 1 (
    echo خطأ: Python غير مثبت أو غير متاح في PATH
    echo يرجى تثبيت Python 3.11+ من: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python متوفر: 
python --version

:: التحقق من إصدار Python
for /f "tokens=2" %%i in ('python --version 2^>nul') do set PYTHON_VERSION=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do set MAJOR=%%a& set MINOR=%%b
if %MAJOR% LSS 3 (
    echo خطأ: يتطلب Python 3.11 أو أحدث
    pause
    exit /b 1
)
if %MAJOR% EQU 3 if %MINOR% LSS 11 (
    echo خطأ: يتطلب Python 3.11 أو أحدث
    pause
    exit /b 1
)

echo إصدار Python مناسب

:: إنشاء البيئة الافتراضية إذا لم تكن موجودة
if not exist ".venv" (
    echo.
    echo إنشاء البيئة الافتراضية...
    python -m venv .venv
    if errorlevel 1 (
    echo خطأ في إنشاء البيئة الافتراضية
        pause
        exit /b 1
    )
    echo تم إنشاء البيئة الافتراضية
) else (
    echo البيئة الافتراضية موجودة
)

:: تفعيل البيئة الافتراضية
echo تفعيل البيئة الافتراضية...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo خطأ في تفعيل البيئة الافتراضية
    pause
    exit /b 1
)

:: تحديث pip
echo تحديث pip...
python -m pip install --upgrade pip

:: تثبيت المكتبات
echo.
echo تثبيت المكتبات المطلوبة...
echo هذا قد يستغرق بضع دقائق...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo خطأ في تثبيت المكتبات
    echo تحقق من اتصال الإنترنت وملف requirements.txt
    pause
    exit /b 1
)
echo تم تثبيت جميع المكتبات بنجاح

:: إنشاء ملف .env إذا لم يكن موجوداً
if not exist ".env" (
    echo.
    echo إنشاء ملف الإعدادات...
    copy .env.example .env >nul
    if errorlevel 1 (
    echo خطأ: لم يتم العثور على .env.example
        pause
        exit /b 1
    )
    echo تم إنشاء ملف .env
) else (
    echo ملف .env موجود
)

:: إنشاء المجلدات المطلوبة
echo.
echo إنشاء المجلدات المطلوبة...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "backups" mkdir backups
if not exist "staticfiles" mkdir staticfiles
echo تم إنشاء جميع المجلدات

:: تطبيق المهاجرات
echo.
echo إعداد قاعدة البيانات...
REM makemigrations should only run during development
python manage.py migrate
if errorlevel 1 (
    echo خطأ في تطبيق المهاجرات
    echo تحقق من إعدادات قاعدة البيانات في .env
    pause
    exit /b 1
)
echo تم إعداد قاعدة البيانات

:: جمع الملفات الثابتة
echo.
echo جمع الملفات الثابتة...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo تحذير: مشكلة في جمع الملفات الثابتة
) else (
    echo تم جمع الملفات الثابتة
)

:: تحميل البيانات التجريبية
echo.
echo تحميل البيانات التجريبية...
python manage.py load_sample_data
if errorlevel 1 (
    echo تحذير: مشكلة في تحميل البيانات التجريبية
    echo يمكنك تحميلها لاحقاً بالأمر: python manage.py load_sample_data
) else (
    echo تم تحميل البيانات التجريبية بنجاح
)

:: فحص النظام
echo.
echo فحص النظام وإصلاح المشاكل...
python manage.py system_self_check --fix
if errorlevel 1 (
    echo يوجد بعض المشاكل في النظام
    echo يمكنك تشغيل: python manage.py system_self_check --fix لإصلاحها
) else (
    echo النظام سليم وجاهز للعمل
)

:: عرض معلومات النظام
echo.
echo ================================================================================
echo تم إعداد Tony ERP بنجاح!
echo ================================================================================
echo.
echo سيتم الوصول إلى النظام على: http://127.0.0.1:8000
echo اسم المستخدم: superadmin
echo كلمة المرور: admin123
echo.
echo روابط مفيدة:
echo    - لوحة الإدارة: http://127.0.0.1:8000/admin/
echo    - واجهة API: http://127.0.0.1:8000/api/docs/
echo    - حالة النظام: http://127.0.0.1:8000/health/ready/
echo.
echo ================================================================================

:: تشغيل الخادم
echo بدء تشغيل الخادم...
echo.
echo لإيقاف الخادم، اضغط Ctrl+C
echo.

:: فتح المتصفح (بعد تأخير قصير)
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000

:: تشغيل خادم Django
python manage.py runserver 127.0.0.1:8000

:: إذا وصلنا هنا فالخادم توقف
echo.
echo تم إيقاف الخادم
echo.
echo لتشغيل النظام مرة أخرى، استخدم:
echo   start_local.bat
echo.
pause