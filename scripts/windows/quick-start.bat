@echo off
REM Tony ERP - Quick Start Script (Windows)
REM سكريبت البدء السريع للمطورين الجدد

echo ========================================
echo   Tony ERP - البدء السريع
echo ========================================
echo.

REM التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python غير مثبت
    echo حمل Python من: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM التحقق من إصدار Python - يجب 3.10 أو أحدث
for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set PYVER=%%V
for /f "tokens=1,2 delims=." %%A in ("%PYVER%") do (
    set PYMAJOR=%%A
    set PYMINOR=%%B
)

if %PYMAJOR% LSS 3 (
    echo خطأ: يجب استخدام Python 3.10 أو أحدث ^(الحالي: %PYVER%^)
    echo حمل أحدث إصدار من: https://www.python.org/downloads/
    pause
    exit /b 1
)

if %PYMAJOR% EQU 3 (
    if %PYMINOR% LSS 10 (
        echo خطأ: يجب استخدام Python 3.10 أو أحدث ^(الحالي: %PYVER%^)
        echo حمل أحدث إصدار من: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo Python %PYVER% مثبت بنجاح
echo.

REM إنشاء بيئة افتراضية
if not exist "venv" (
    echo إنشاء بيئة افتراضية...
    python -m venv venv
)

REM تفعيل البيئة الافتراضية
echo تفعيل البيئة الافتراضية...
call venv\Scripts\activate.bat

REM تثبيت المتطلبات
echo تثبيت المتطلبات...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM إنشاء ملف .env
if not exist ".env" (
    echo إنشاء ملف .env...
    echo DEBUG=True > .env
    echo SECRET_KEY=your-secret-key-here >> .env
    echo ALLOWED_HOSTS=localhost,127.0.0.1 >> .env
    echo DATABASE_URL=sqlite:///db.sqlite3 >> .env
    echo LANGUAGE_CODE=ar >> .env
    echo TIME_ZONE=Asia/Riyadh >> .env
    echo تم إنشاء .env
)

REM إنشاء المجلدات
echo إنشاء المجلدات...
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
if not exist "media" mkdir media
if not exist "staticfiles" mkdir staticfiles

REM تطبيق المهاجرات
echo تطبيق مهاجرات قاعدة البيانات...
python manage.py migrate

REM جمع الملفات الثابتة
echo جمع الملفات الثابتة...
python manage.py collectstatic --noinput

REM إنشاء مستخدم admin
echo.
echo إنشاء مستخدم admin...
python manage.py shell < nul > nul 2>&1
python -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@tony-erp.local', 'admin123') if not User.objects.filter(username='admin').exists() else print('المستخدم admin موجود')"

echo.
echo ========================================
echo الإعداد مكتمل!
echo ========================================
echo.
echo لتشغيل الخادم:
echo   python manage.py runserver
echo.
echo الروابط:
echo   Dashboard: http://localhost:8000
echo   Admin: http://localhost:8000/admin/
echo   API Docs: http://localhost:8000/api/docs/
echo.
echo تسجيل الدخول:
echo   Username: admin
echo   Password: admin123
echo.
pause
