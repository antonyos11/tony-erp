@echo off
chcp 65001
echo =======================================
echo    نظام الصيانة والمعدات - تشغيل سريع
echo =======================================
echo.

echo بدء تشغيل نظام الصيانة...
echo.

cd /d "d:\الشامل"

echo التحقق من قاعدة البيانات...
python manage.py migrate

echo.
echo بدء تشغيل الخادم...
echo.
echo روابط الوصول:
echo    - النظام الرئيسي: http://localhost:8000/
echo    - نظام الصيانة: http://localhost:8000/maintenance/
echo    - لوحة الإدارة: http://localhost:8000/admin/
echo.
echo لإيقاف الخادم اضغط Ctrl+C
echo.

python manage.py runserver 0.0.0.0:8000

pause