@echo off
chcp 65001 >nul 2>&1
title Tony ERP - تشغيل النظام محلياً

echo.
echo ================================================================================
echo Tony ERP - تشغيل النظام محلياً
echo ================================================================================
echo.

:: اختيار Python 3.11+ بشكل موثوق
set "PYCMD="
setlocal EnableDelayedExpansion
for %%C in (python "py -3.12" "py -3.11" "py -3") do (
    if not defined PYCMD (
        set "__cand__=%%~C"
        call :__try_py
    )
)
endlocal & set "PYCMD=%PYCMD%"
if not defined PYCMD (
        echo خطأ: لم يتم العثور على Python 3.11 أو أحدث في PATH
        pause
        exit /b 1
)

:: تفعيل البيئة الافتراضية (محلية أو في المجلد الأعلى)
set "VENV_DIR=.venv"
if not exist "%VENV_DIR%\Scripts\activate.bat" set "VENV_DIR=..\.venv"
if not exist "%VENV_DIR%\Scripts\activate.bat" (
        echo فشل: البيئة الافتراضية غير موجودة (.venv)
        echo يرجى تشغيل setup_windows.bat أولاً
        pause
        exit /b 1
)
echo تفعيل البيئة الافتراضية من %VENV_DIR% ...
call "%VENV_DIR%\Scripts\activate.bat"

:: التحقق من وجود ملف .env
if not exist ".env" (
    echo فشل: ملف .env غير موجود
    echo يرجى تشغيل setup_windows.bat أولاً
    pause
    exit /b 1
)

:: فحص سريع للنظام
echo فحص سريع للنظام...
%PYCMD% manage.py system_self_check
if errorlevel 1 (
    echo يوجد مشاكل في النظام
    echo شغّل: python manage.py system_self_check --fix لإصلاحها
    echo.
    set /p continue="هل تريد المتابعة؟ (y/n): "
    if /i not "%continue%"=="y" (
        pause
        exit /b 1
    )
)

echo.
echo النظام جاهز للتشغيل
echo.
echo العنوان: http://127.0.0.1:8000
echo المستخدم: superadmin
echo كلمة المرور: admin123
echo.
echo لإيقاف الخادم، اضغط Ctrl+C
echo.

:: فتح المتصفح
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000

:: تشغيل الخادم
%PYCMD% manage.py runserver 127.0.0.1:8000

echo.
echo تم إيقاف الخادم
pause

goto :eof

:__try_py
call %__cand__% -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 set "PYCMD=%__cand__%"
exit /b 0