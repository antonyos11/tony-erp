@echo off
chcp 65001 >nul
title Tony ERP Print Agent - تثبيت سريع

echo.
echo ══════════════════════════════════════════════════════════════
echo       Tony ERP - Print Agent - تثبيت بسيط وسريع
echo ══════════════════════════════════════════════════════════════
echo.

REM التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [خطأ] Python غير مثبت!
    echo.
    echo حمّل Python من: https://www.python.org/downloads/
    echo مهم: اختر "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [✓] Python مثبت
python --version
echo.

echo جاري تثبيت المكتبات...
echo.

echo [1/2] تثبيت websockets...
pip install websockets --user
echo.

echo [2/2] تثبيت pywin32...
pip install pywin32 --user
echo.

echo إعداد pywin32...
python -m pywin32_postinstall -install
echo.

echo ══════════════════════════════════════════════════════════════
echo   ✓ اكتمل التثبيت!
echo.
echo   الآن شغّل: run_windows.bat
echo ══════════════════════════════════════════════════════════════
pause
