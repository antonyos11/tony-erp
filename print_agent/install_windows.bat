@echo off
REM Tony ERP Print Agent - تثبيت على Windows
REM يجب تشغيله كمسؤول (Run as Administrator)

echo ========================================
echo    Tony ERP Print Agent - تثبيت
echo ========================================
echo.

REM التحقق من Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python غير مثبت!
    echo يرجى تثبيت Python 3.8 أو أحدث من:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] تثبيت المكتبات المطلوبة...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] فشل تثبيت المكتبات
    pause
    exit /b 1
)

echo.
echo [2/4] إنشاء اختصار لسطح المكتب...
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%USERPROFILE%\Desktop\Tony Print Agent.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%CD%\start_agent.bat" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%CD%" >> CreateShortcut.vbs
echo oLink.Description = "Tony ERP Print Agent" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs
cscript CreateShortcut.vbs
del CreateShortcut.vbs

echo.
echo [3/4] إنشاء ملف التشغيل...
(
echo @echo off
echo cd /d "%%~dp0"
echo python agent.py
echo pause
) > start_agent.bat

echo.
echo [4/4] تسجيل كخدمة Windows Service (اختياري)...
echo يمكنك تشغيل الخدمة تلقائيًا مع Windows باستخدام NSSM أو Task Scheduler

echo.
echo ========================================
echo    ✓ اكتمل التثبيت بنجاح!
echo ========================================
echo.
echo لتشغيل الخدمة:
echo   1. افتح: start_agent.bat
echo   2. أو استخدم الاختصار على سطح المكتب
echo.
echo الخدمة ستعمل على: ws://localhost:9876
echo.
pause
