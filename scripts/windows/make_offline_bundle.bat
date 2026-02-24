@echo off
chcp 65001 >nul 2>&1
title تحضير حزم التشغيل بدون إنترنت

echo.
echo تحضير باقة الحزم للتثبيت بدون إنترنت (vendor\wheels)
echo هذا سيقوم بتحميل جميع الحزم المطلوبة إلى مجلد محلي.
echo.

cd /d "%~dp0"

set "PYCMD=python"
py -3 --version >nul 2>&1
if %ERRORLEVEL%==0 set "PYCMD=py -3"

%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo Python غير متاح. ثبّت Python ثم أعد المحاولة.
  pause
  exit /b 1
)

set "WHEEL_DIR=vendor\wheels"
if not exist vendor mkdir vendor >nul 2>&1
if not exist "%WHEEL_DIR%" mkdir "%WHEEL_DIR%" >nul 2>&1

echo تحديث pip ...
%PYCMD% -m pip install --upgrade pip >nul

echo تنزيل الحزم إلى %WHEEL_DIR% ...
%PYCMD% -m pip download -r requirements.txt -d "%WHEEL_DIR%"
if errorlevel 1 (
  echo فشل تنزيل الحزم. تحقق من الاتصال.
  pause
  exit /b 1
)

echo تم تجهيز الحزم. الآن يمكنك نقل مجلد vendor\wheels مع المشروع إلى جهاز آخر.
pause
