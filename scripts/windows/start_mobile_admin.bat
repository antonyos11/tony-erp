@echo off
:: تشغيل النظام للموبايل + فتح المنفذ 8000 تلقائياً
:: (يجب تشغيل هذا الملف بزر يمين > Run as administrator)

net session >nul 2>&1 || (
  echo لابد من تشغيل الملف كمسؤول (Right click > Run as administrator)
  pause
  exit /b 1
)

cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo لم يتم العثور على البيئة الافتراضية .venv
  echo تأكد من تثبيت المتطلبات:  pip install -r requirements.txt
  pause
  exit /b 1
)
call .\.venv\Scripts\activate.bat

echo جمع كل عناوين IPv4 المتاحة...
setlocal enabledelayedexpansion
set firstLan=
set firstWifi=
set iplist=
for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
  set raw=%%I
  set raw=!raw: =!
  for /f "delims=" %%A in ("!raw!") do (
    set ip=%%A
    if not "!ip!"=="127.0.0.1" (
      echo   - !ip!
      set iplist=!iplist! !ip!
      echo !ip! | findstr /R /C:"^192\.168\." >nul && (
        if not defined firstLan set firstLan=!ip!
      )
      echo !ip! | findstr /I "wi" >nul && (
        if not defined firstWifi set firstWifi=!ip!
      )
    )
  )
)

if defined firstWifi (set chosen=!firstWifi!) else if defined firstLan (set chosen=!firstLan!) else for %%Z in (!iplist!) do if not defined chosen set chosen=%%Z

if not defined chosen set chosen=127.0.0.1
endlocal & set chosen=%chosen%

echo.
echo فتح المنفذ في الجدار الناري...
netsh advfirewall firewall delete rule name="TONY_ERP_DEV_8000" >nul 2>&1
netsh advfirewall firewall add rule name="TONY_ERP_DEV_8000" dir=in action=allow protocol=TCP localport=8000 profile=any >nul 2>&1 && echo تم السماح للمنفذ 8000.

echo.
echo العنوان المقترح (جرّبه على الموبايل بعد تشغيل السيرفر):
echo   http://%chosen%:8000/
echo لو لم يعمل جرّب عنواناً آخر من القائمة أعلاه.
echo.

python manage.py runserver 0.0.0.0:8000

pause
