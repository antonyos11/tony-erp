@echo off
chcp 65001 >nul
title Tony ERP Print Agent - Windows

echo.
echo ══════════════════════════════════════════════════════════════
echo           Tony ERP - Print Agent v2.0 (Windows)
echo           خدمة الطباعة للطابعات الحرارية XPrinter
echo ══════════════════════════════════════════════════════════════
echo.

REM التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [خطأ] Python غير مثبت!
    echo.
    echo يرجى تثبيت Python أولاً:
    echo https://www.python.org/downloads/
    echo.
    echo مهم: اختر "Add Python to PATH" عند التثبيت
    echo.
    pause
    exit /b 1
)

echo [✓] Python مثبت
echo.

REM التحقق من المكتبات
echo [1/3] التحقق من websockets...
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo      جاري تثبيت websockets...
    pip install websockets --user
    if errorlevel 1 (
        echo      [تحذير] فشل التثبيت، محاولة بدون --user...
        pip install websockets
    )
)
echo      [✓] websockets جاهز

echo.
echo [2/3] التحقق من pywin32...
python -c "import win32print" >nul 2>&1
if errorlevel 1 (
    echo      جاري تثبيت pywin32...
    pip install pywin32 --user
    if errorlevel 1 (
        echo      [تحذير] فشل التثبيت، محاولة بدون --user...
        pip install pywin32
    )
    echo      جاري إعداد pywin32...
    python -m pywin32_postinstall -install 2>nul
)
echo      [✓] pywin32 جاهز

echo.
echo [3/3] فحص الطابعات...
python -c "import win32print; printers = win32print.EnumPrinters(6); print(f'      تم اكتشاف {len(printers)} طابعة')"
if errorlevel 1 (
    echo      [تحذير] لم يتم اكتشاف طابعات
)

echo.
echo ══════════════════════════════════════════════════════════════
echo   تشغيل خدمة الطباعة...
echo   الخدمة تعمل على: ws://localhost:9876
echo.
echo   لإيقاف الخدمة: اضغط Ctrl+C
echo ══════════════════════════════════════════════════════════════
echo.

python agent_windows.py

echo.
echo ══════════════════════════════════════════════════════════════
echo   تم إيقاف الخدمة
echo ══════════════════════════════════════════════════════════════
pause
