@echo off
:: إنشاء قواعد الجدار الناري للسماح بالوصول إلى خادم Django من الأجهزة الأخرى
:: يجب تشغيل هذا الملف كمسؤول (Run as Administrator)

net session >nul 2>&1 || (
  echo يجب تشغيل هذا الملف كمسؤول (Right click > Run as administrator)
  pause
  exit /b 1
)

set PYEXE="d:\الشامل\.venv\Scripts\python.exe"

echo حذف القواعد القديمة (إن وجدت)...
netsh advfirewall firewall delete rule name="Django Python Allow" >nul 2>&1
netsh advfirewall firewall delete rule name="Django Port 8000" >nul 2>&1
netsh advfirewall firewall delete rule name="Django Port 9000" >nul 2>&1

echo إضافة قاعدة سماح للبرنامج Python...
netsh advfirewall firewall add rule name="Django Python Allow" dir=in action=allow program=%PYEXE% enable=yes profile=any || echo تحذير: فشل إضافة قاعدة البرنامج

echo إضافة قاعدة منفذ 8000...
netsh advfirewall firewall add rule name="Django Port 8000" dir=in action=allow protocol=TCP localport=8000 profile=any || echo تحذير: فشل إضافة منفذ 8000

echo إضافة قاعدة منفذ 9000 (اختبار احتياطي)...
netsh advfirewall firewall add rule name="Django Port 9000" dir=in action=allow protocol=TCP localport=9000 profile=any || echo تحذير: فشل إضافة منفذ 9000

echo.
echo تم التنفيذ. شغّل الآن:
echo    start_mobile.bat   (أو)   python manage.py runserver 0.0.0.0:8000

echo لو ما زال لا يعمل:
echo  - تأكد أن الشبكة Private:  Get-NetConnectionProfile
echo  - لو Public:  Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private

echo انتهى.
pause
