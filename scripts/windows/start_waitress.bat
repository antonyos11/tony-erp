@echo off
REM تشغيل النظام عبر Waitress كسيرفر WSGI خفيف للإنتاج الداخلي
cd /d D:\الشامل
call .venv\Scripts\activate.bat
waitress-serve --listen=0.0.0.0:8000 accountant_pro.wsgi:application
