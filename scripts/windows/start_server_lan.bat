@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion
title Tony ERP - تشغيل الخادم على الشبكة المحلية (LAN)

:: الانتقال لمجلد المشروع
cd /d "%~dp0"

:: اختيار Python المتاح
set "PYCMD=python"
py -3 --version >nul 2>&1
if %ERRORLEVEL%==0 set "PYCMD=py -3"

%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo خطأ: Python غير مثبت أو غير متاح في PATH. رجاءً ثبّت Python 3.11+.
  pause
  exit /b 1
)

:: إنشاء البيئة الافتراضية إن لزم
if not exist .venv (
  echo إنشاء البيئة الافتراضية .venv ...
  %PYCMD% -m venv .venv || ( echo فشل إنشاء البيئة && pause && exit /b 1 )
)
call .venv\Scripts\activate.bat || ( echo فشل تفعيل البيئة && pause && exit /b 1 )

:: تحديث pip وتثبيت المتطلبات (استخدم الحزم المحلية إن توفرت)
echo تحديث pip ...
python -m pip install --upgrade pip >nul
set "WHEEL_DIR=vendor\wheels"
if exist "%WHEEL_DIR%" (
  dir /b "%WHEEL_DIR%\*.whl" >nul 2>&1 && (
    echo تثبيت المتطلبات من الحزم المحلية ...
    python -m pip install --no-index --find-links "%WHEEL_DIR%" -r requirements.txt || ( echo فشل التثبيت && pause && exit /b 1 )
  ) || (
    echo تثبيت المتطلبات من الإنترنت ...
    python -m pip install -r requirements.txt || ( echo فشل التثبيت && pause && exit /b 1 )
  )
  ) else (
  echo تثبيت المتطلبات من الإنترنت ...
  python -m pip install -r requirements.txt || ( echo فشل التثبيت && pause && exit /b 1 )
)

:: إنشاء .env من المثال إذا لزم
if not exist .env if exist .env.example (
  copy /y .env.example .env >nul
)

:: تطبيق المهاجرات وجمع الملفات الثابتة
echo تطبيق المهاجرات ...
python manage.py migrate --noinput || ( echo خطأ بالمهاجرات && pause && exit /b 1 )
echo جمع الملفات الثابتة ...
python manage.py collectstatic --noinput >nul

:: إيجاد منفذ متاح (8000..8005)
set "FREEPORT=8000"
for %%P in (8000 8001 8002 8003 8004 8005) do (
  >nul 2>&1 (netstat -ano | findstr ":%%P" | findstr LISTENING)
  if errorlevel 1 (
    set "FREEPORT=%%P"
    goto :PORT_FOUND
  )
)
:PORT_FOUND
echo استخدام المنفذ %FREEPORT%

:: إضافة استثناء جدار الحماية (يتجاهل الفشل)
netsh advfirewall firewall add rule name="TonyERP %FREEPORT%" dir=in action=allow protocol=TCP localport=%FREEPORT% profile=any >nul 2>&1

:: تشغيل خادم LAN
echo تشغيل خادم الشبكة المحلية ...
python start_network_server.py

echo.
echo تم إيقاف الخادم.
pause
