@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion
title Tony ERP - تجهيز نسخة محمولة لأي جهاز (Windows)

echo.
echo ======================================================================
echo  تجهيز نسخة محمولة للتشغيل على أي كمبيوتر Windows
echo  - إنشاء/تحديث ملف .env من .env.example وإضافة IP المحلي إلى ALLOWED_HOSTS
echo  - تنزيل حزم المتطلبات إلى vendor\wheels للتثبيت بدون إنترنت
echo  - التحقق السريع من المهاجرات والملفات الثابتة (اختياري)
echo ======================================================================
echo.

cd /d "%~dp0"

:: اختيار Python المناسب
set "PYCMD=python"
py -3 --version >nul 2>&1
if %ERRORLEVEL%==0 set "PYCMD=py -3"

%PYCMD% --version >nul 2>&1
if errorlevel 1 (
  echo خطأ: Python غير مثبت أو غير متاح في PATH
  echo رجاءً ثبّت Python 3.11+ ثم أعد المحاولة.
  pause
  exit /b 1
)

echo.
echo 1) إعداد ملف البيئة .env ...
if not exist .env (
  if exist .env.example (
    copy /y .env.example .env >nul
    if errorlevel 1 (
      echo تعذّر إنشاء .env من .env.example
      pause
      exit /b 1
    )
  ) else (
    echo تحذير: لا يوجد .env.example. تخطٍ.
  )
)

:: الحصول على IP المحلي (أول IPv4 نشط)
for /f "tokens=2 delims=: " %%I in ('ipconfig ^| findstr /r /c:"IPv4"') do (
  set "LOCAL_IP=%%I"
  goto :HAVE_IP
)
:HAVE_IP
set "LOCAL_IP=%LOCAL_IP: =%"
if not defined LOCAL_IP set "LOCAL_IP=127.0.0.1"
echo - IP المحلي المكتشف: %LOCAL_IP%

:: تحديث ALLOWED_HOSTS داخل .env عبر سكربت بايثون صغير
"%PYCMD%" prepare_portable.py --ip "%LOCAL_IP%" >nul 2>&1
if errorlevel 1 (
  echo تحذير: لم نستطع تحديث ALLOWED_HOSTS تلقائياً. يمكن التعديل يدوياً داخل .env
)

echo.
echo 2) إنشاء بيئة افتراضية (إن لزم) وتحديث pip ...
if not exist .venv (
  %PYCMD% -m venv .venv
  if errorlevel 1 (
    echo فشل إنشاء البيئة الافتراضية.
    pause
    exit /b 1
  )
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul

echo.
echo 3) تنزيل حزم المتطلبات للوضع غير المتصل (vendor\wheels) ...
set "WHEEL_DIR=vendor\wheels"
if not exist "%WHEEL_DIR%" mkdir "%WHEEL_DIR%"
python -m pip download -r requirements.txt -d "%WHEEL_DIR%"
if errorlevel 1 (
  echo تحذير: فشل تنزيل بعض الحزم. سيحاول start_anywhere التثبيت عبر الإنترنت.
)

echo.
set /p RUNMIG=هل تريد تطبيق المهاجرات وجمع الملفات الثابتة الآن؟ [y/N]: 
if /I "%RUNMIG%"=="Y" (
  echo تشغيل migrate ...
  python manage.py migrate --noinput || echo تحذير: خطأ بالمهاجرات
  echo جمع الملفات الثابتة ...
  python manage.py collectstatic --noinput || echo تحذير: خطأ بجمع الملفات الثابتة
)

echo.
echo ======================================================================
echo  تم تجهيز النسخة المحمولة بنجاح.
echo  انسخ هذا المجلد إلى أي جهاز، ثم شغّل start_anywhere.bat هناك.
echo  ملاحظات:
echo    - الحزم داخل vendor\wheels تناسب Windows الحالي (قد لا تناسب أنظمة أخرى)
echo    - يمكن تعديل .env حسب الحاجة قبل النسخ
echo ======================================================================
echo.
pause
