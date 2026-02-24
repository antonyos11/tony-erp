@echo off
chcp 65001 >nul 2>&1
title Tony ERP - Restore Backup
cd /d "%~dp0"

if "%~1"=="" (
  echo الاستخدام: restore_backup.bat ^<مسار_مجلد_النسخة^>
  echo مثال: restore_backup.bat backups\backup_20250822_1200
  pause
  exit /b 1
)

set "SRC=%~1"
if not exist "%SRC%" (
  echo المسار غير موجود: %SRC%
  pause
  exit /b 1
)

echo استعادة قاعدة البيانات والملفات من %SRC% ...
if exist "%SRC%\db.sqlite3" copy /y "%SRC%\db.sqlite3" db.sqlite3 >nul 2>&1
if exist "%SRC%\media" robocopy "%SRC%\media" media /E >nul 2>&1
echo تم الاستعادة.
echo طبّق المهاجرات للتأكد من توافق القاعدة:
echo   .venv\Scripts\python.exe manage.py migrate --noinput
pause
