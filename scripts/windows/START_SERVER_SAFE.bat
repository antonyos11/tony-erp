@echo off
chcp 65001 > nul
title Tony ERP Server - Safe Start

echo.
echo ===============================================================================
echo                     Tony ERP - بدء الخادم الآمن
echo ===============================================================================
echo.

cd /d "%~dp0"

echo [1/4] تنظيف المنافذ القديمة...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    echo إيقاف العملية: %%a
    taskkill /F /PID %%a > nul 2>&1
)

echo [2/4] التأكد من البيئة الافتراضية...
if not exist ".venv_new\Scripts\python.exe" (
    echo ❌ خطأ: البيئة الافتراضية غير موجودة!
    pause
    exit /b 1
)

echo [3/4] فحص قاعدة البيانات...
".venv_new\Scripts\python.exe" manage.py check --deploy

echo [4/4] بدء الخادم...
echo.
echo ===============================================================================
echo                 الخادم يعمل على http://127.0.0.1:8000
echo                 للإيقاف: اضغط Ctrl+C
echo ===============================================================================
echo.

".venv_new\Scripts\python.exe" manage.py runserver 127.0.0.1:8000 --noreload

echo.
echo الخادم متوقف.
pause
