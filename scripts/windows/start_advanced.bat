@echo off
chcp 65001 >nul
title نظام الشامل - مدير النظام المتقدم

echo.
echo ============================================
echo نظام الشامل - مدير النظام المتقدم
echo ============================================
echo.

:: الانتقال لمجلد المشروع
cd /d "%~dp0"

:: التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo فشل: Python غير مثبت
    echo يرجى تثبيت Python 3.8 أو أحدث من: https://python.org
    pause
    exit /b 1
)

:: تفعيل البيئة الافتراضية
if exist ".venv\Scripts\activate.bat" (
    echo تفعيل البيئة الافتراضية...
    call .venv\Scripts\activate.bat
)

:: تشغيل مدير النظام
python system_manager.py

echo.
echo تم إغلاق النظام
pause