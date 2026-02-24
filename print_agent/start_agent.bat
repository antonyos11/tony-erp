@echo off
chcp 65001 >nul

REM التأكد من أننا في المجلد الصحيح
cd /d "%~dp0"

REM Tony ERP Print Agent - تشغيل سريع
REM استخدم هذا الملف لتشغيل الخدمة بسرعة

title Tony ERP Print Agent

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║           Tony ERP - Print Agent v1.0                     ║
echo ║           خدمة الطباعة المباشرة                          ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python غير مثبت!
    echo يرجى تثبيت Python أولاً من: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [✓] Python مثبت
echo.

REM التحقق من المكتبات
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo [!] المكتبات غير مثبتة - جاري التثبيت...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] فشل تثبيت المكتبات
        pause
        exit /b 1
    )
    echo [✓] تم تثبيت المكتبات
)

echo [✓] المكتبات جاهزة
echo.

REM تشغيل الخدمة
echo ═══════════════════════════════════════════════════════════
echo   🚀 تشغيل خدمة الطباعة...
echo ═══════════════════════════════════════════════════════════
echo.
echo الخدمة ستعمل على: ws://localhost:9876
echo لإيقاف الخدمة: اضغط Ctrl+C
echo.
echo ═══════════════════════════════════════════════════════════
echo.

REM التحقق من وجود agent_windows.py (للويندوز) أو agent.py
if exist agent_windows.py (
    echo [*] تشغيل نسخة Windows المحسّنة...
    python agent_windows.py
) else (
    python agent.py
)

REM عند الإيقاف
echo.
echo ═══════════════════════════════════════════════════════════
echo   تم إيقاف الخدمة
echo ═══════════════════════════════════════════════════════════
pause
