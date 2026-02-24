@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion
title Tony ERP - بناء نسخة مجلد واحد مع أيقونة تشغيل

cd /d "%~dp0.."  || ( echo فشل تغيير المجلد && pause && exit /b 1 )

set "DIST_ROOT=dist"
set "DIST_NAME=TonyERP"
set "DIST_DIR=%DIST_ROOT%\%DIST_NAME%"
set "APP_DIR=%DIST_DIR%\app"

if not exist "%DIST_ROOT%" mkdir "%DIST_ROOT%"
if exist "%DIST_DIR%" (
  echo حذف نسخة سابقة ...
  rmdir /s /q "%DIST_DIR%"
)

echo إنشاء هيكل التوزيع ...
mkdir "%APP_DIR%" || ( echo فشل إنشاء المجلد && pause && exit /b 1 )

echo نسخ ملفات التطبيق إلى app/ (استثناء المجلدات غير الضرورية) ...
rem Robocopy: /MIR يعكس البنية، استثناء .git, dist, .venv, __pycache__, *.pyc, vendor\wheels اختيارياً يتم نسخها لاحقاً
robocopy . "%APP_DIR%" /MIR ^
  /XD .git dist .venv __pycache__ packaging \\?\%APP_DIR%\vendor\wheels ^
  /XF *.pyc *.pyo *.log *.tmp ^
  /NFL /NDL /NJH /NJS /NP >nul

if errorlevel 8 (
  echo تحذير: Robocopy أعاد رمز %ERRORLEVEL% (قد تكون اختلافات ملفات)
)

echo تضمين حزم vendor\wheels إن كانت موجودة ...
if exist vendor\wheels (
  robocopy vendor\wheels "%APP_DIR%\vendor\wheels" /E /NFL /NDL /NJH /NJS /NP >nul
)

echo إنشاء مُشغّل وحيد في الجذر ...
>"%DIST_DIR%\تشغيل Tony ERP.bat" (
  echo @echo off
  echo chcp 65001 ^>nul 2^>^&1
  echo cd /d %~dp0app
  echo call start_server_lan.bat
)

echo إنشاء README مختصر ...
>"%DIST_DIR%\README_تشغيل.txt" (
  echo لتشغيل النظام: انقر على ^"تشغيل Tony ERP.bat^".
  echo سيتم تشغيل الخادم على الشبكة المحلية ويمكن الوصول إليه من الأجهزة على نفس الـ Wi-Fi.
  echo اسم الدخول الافتراضي: superadmin / admin123
)

echo (اختياري) إنشاء اختصار على سطح المكتب ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1" -TargetPath "%DIST_DIR%\تشغيل Tony ERP.bat" -ShortcutName "تشغيل Tony ERP" -IconPath "%SystemRoot%\System32\shell32.dll" -IconIndex 220  >nul 2>&1

echo.
echo تم تجهيز المجلد: %DIST_DIR%
echo انسخ هذا المجلد إلى جهاز الخادم وشغّل ^"تشغيل Tony ERP.bat^" فقط.
echo.
pause
