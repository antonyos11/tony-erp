@echo off
chcp 65001 >nul
title نظام الشامل - خادم الشبكة المحلية

echo.
echo ===================================================
echo نظام الشامل للمحاسبة والإدارة
echo ===================================================
echo.

:: الانتقال لمجلد المشروع
cd /d "%~dp0"

:: التحقق من وجود Python
python --version >nul 2>&1
if errorlevel 1 (
    echo فشل: Python غير مثبت أو غير موجود في PATH
    echo يرجى تثبيت Python 3.8 أو أحدث
    pause
    exit /b 1
)

:: تفعيل البيئة الافتراضية إذا كانت موجودة
if exist ".venv\Scripts\activate.bat" (
    echo تفعيل البيئة الافتراضية...
    call .venv\Scripts\activate.bat
)

:: تشغيل سكريبت Python
echo بدء تشغيل نظام الشبكة المحلية...
python start_network_server.py

:: إنهاء
echo.
echo تم إنهاء النظام
pause