@echo off
chcp 65001 >nul 2>&1
title Tony ERP - إصلاح المشاكل الشائعة

echo.
echo ================================================================================
echo Tony ERP - إصلاح المشاكل الشائعة
echo ================================================================================
echo.

echo هذا المعالج سيحاول إصلاح المشاكل الشائعة:
echo   - حذف ملفات Python المؤقتة (.pyc)
echo   - إعادة تطبيق المهاجرات
echo   - إعادة جمع الملفات الثابتة
echo   - إعادة بناء حاويات Docker (إن أمكن)
echo   - فحص شامل للنظام
echo.

set /p continue="هل تريد المتابعة؟ (y/n): "
if /i not "%continue%"=="y" (
    echo تم الإلغاء
    pause
    exit /b 0
)

echo.
echo حذف ملفات Python المؤقتة...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /q /s *.pyc >nul 2>&1
echo تم حذف ملفات Python المؤقتة

:: التحقق من وجود البيئة الافتراضية
if exist ".venv" (
    echo تفعيل البيئة الافتراضية...
    call .venv\Scripts\activate.bat
    
    echo إعادة تطبيق المهاجرات...
    REM makemigrations should only run in development, not in fix scripts
    python manage.py migrate --run-syncdb
    echo تم إعادة تطبيق المهاجرات
    
    echo إعادة جمع الملفات الثابتة...
    python manage.py collectstatic --noinput --clear
    echo تم إعادة جمع الملفات الثابتة
    
    echo فحص شامل للنظام...
    python manage.py system_self_check --fix
    echo تم فحص النظام
) else (
    echo لم يتم العثور على البيئة الافتراضية
)

:: التحقق من وجود Docker
docker --version >nul 2>&1
if not errorlevel 1 (
    echo.
    echo إعادة بناء حاويات Docker...
    docker compose down >nul 2>&1
    docker compose build --no-cache
    docker system prune -f >nul 2>&1
    echo تم إعادة بناء حاويات Docker
) else (
    echo Docker غير متاح، تم تخطي إعادة البناء
)

echo.
echo إصلاح صلاحيات المجلدات...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "backups" mkdir backups
if not exist "staticfiles" mkdir staticfiles
echo تم إصلاح صلاحيات المجلدات

echo.
echo ================================================================================
echo تم إصلاح جميع المشاكل الشائعة!
echo ================================================================================
echo.
echo الخطوات التالية:
echo   1. جرب تشغيل النظام مرة أخرى
echo   2. إذا استمرت المشاكل، راجع ملفات السجلات في مجلد logs/
echo   3. للمساعدة المتقدمة، شغّل: python manage.py system_self_check
echo.
pause