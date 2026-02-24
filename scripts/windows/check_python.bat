@echo off
chcp 65001 >nul 2>&1

echo ================================================================================
echo فحص Python في النظام
echo ================================================================================
echo.

:: التحقق من Python باستخدام py
echo جاري فحص Python...
py --version >nul 2>&1
if errorlevel 1 (
    echo فشل: Python غير مثبت أو غير متاح في النظام
    echo.
    echo حلول مقترحة:
    echo    1. تحميل Python من: https://python.org/downloads/
    echo    2. تأكد من اختيار "Add Python to PATH" أثناء التثبيت
    echo    3. أعد تشغيل Command Prompt بعد التثبيت
    echo.
    pause
    exit /b 1
) else (
    echo Python متوفر:
    py --version
)

echo.
echo جاري فحص pip...
py -m pip --version >nul 2>&1
if errorlevel 1 (
    echo فشل: pip غير متاح
) else (
    echo pip متوفر:
    py -m pip --version
)

echo.
echo جاري فحص Django...
if exist manage.py (
    echo ملف manage.py موجود
    py manage.py --version 2>nul
    if errorlevel 1 (
        echo فشل: Django غير مثبت أو يحتاج تثبيت المتطلبات
    echo نفّذ: py -m pip install -r requirements.txt
    ) else (
    echo Django متاح
        echo.
    echo بدء تشغيل فحص النظام...
        py manage.py system_self_check
    )
) else (
    echo فشل: ملف manage.py غير موجود
    echo تأكد من أنك في مجلد المشروع الصحيح
)

echo.
pause