@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion
rem Enforce UTF-8 mode for all spawned Python processes to avoid cp1252 decode errors
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
title Tony ERP - تشغيل فوري على أي كمبيوتر

echo.
echo ======================================================================
echo  تشغيل النظام على أي كمبيوتر (Windows)
echo  - ينشئ بيئة افتراضية تلقائياً
echo  - يثبت المتطلبات
echo  - يطبق المهاجرات ويجمع الملفات الثابتة
echo  - يشغل الخادم محلياً أو على الشبكة المحلية
echo ======================================================================
echo.

:: الانتقال لمجلد المشروع
cd /d "%~dp0"

:: اختيار Python 3.11+ بشكل موثوق لتجنب مشاكل py launcher
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
  echo خطأ: لم يتم العثور على Python 3.11 أو أحدث.
  echo يرجى تثبيت Python 3.11+ من https://www.python.org/downloads/ ثم حاول مجدداً.
  pause
  exit /b 1
)

for /f "tokens=2" %%v in ('%PYCMD% --version 2^>nul') do set "PYVER=%%v"
echo Python: %PYVER%

goto :__after_py_detect

:__try_py
rem يتحقق أن الإصدار 3.11+ وأن التنفيذ يعمل فعلاً
call %__cand__% -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)" >nul 2>&1
if not errorlevel 1 set "PYCMD=%__cand__%"
exit /b 0

:__after_py_detect

:: تحديد مجلد البيئة: استخدم .venv في الجذر إن وجد، وإلا أنشئه في الجذر
set "ROOT_VENV=..\.venv"
set "APP_VENV=.venv"
set "VENV_DIR="
rem الأفضلية لبيئة التطبيق المحلية أولاً، ثم الجذر
if exist "%APP_VENV%\Scripts\activate.bat" set "VENV_DIR=%APP_VENV%"
if not defined VENV_DIR if exist "%ROOT_VENV%\Scripts\activate.bat" set "VENV_DIR=%ROOT_VENV%"
if not defined VENV_DIR (
  echo.
  echo إنشاء البيئة الافتراضية في مجلد التطبيق .\.venv ...
  %PYCMD% -m venv "%APP_VENV%"
  if errorlevel 1 (
    echo فشل إنشاء البيئة الافتراضية.
    pause
    exit /b 1
  )
  set "VENV_DIR=%APP_VENV%"
)

:: تفعيل البيئة
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo فشل تفعيل البيئة الافتراضية.
  pause
  exit /b 1
)

:: تحديث pip وتثبيت المتطلبات (أولوية للوضع غير المتصل إن توفرت الحزم محلياً)
echo التحقق من المكتبات الأساسية ...
set "SKIP_PIP=0"
rem لا نتخطى التثبيت إلا إذا توفرت الحزم الأساسية كلها
python -c "import sys; import django, rest_framework, django_filters, corsheaders; sys.exit(0)" >nul 2>&1
if not errorlevel 1 set "SKIP_PIP=1"

echo إعداد pip ...
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_PYTHON_VERSION_WARNING=1"
if "%SKIP_PIP%"=="1" (
  echo تم العثور على Django بالفعل ^(تخطي تثبيت المتطلبات^)
) else (
  echo تثبيت المتطلبات ...
  set "PIP_DEFAULT_TIMEOUT=20"
  echo - تحديث pip ^(قد يستغرق أقل من دقيقة^) ...
  python -m pip install --upgrade pip --disable-pip-version-check --timeout 20 --retries 1 >nul 2>&1
  if errorlevel 1 (
    echo تحذير: تعذر تحديث pip حالياً ^(متابعة بدون تحديث^)
  )
  set "WHEEL_DIR=vendor\wheels"
  set "PIP_COMMON=python -m pip install -q --disable-pip-version-check"
  if exist requirements.txt (
    if exist "%WHEEL_DIR%\*.whl" (
      echo محاولة التثبيت من الحزم المحلية ^(%WHEEL_DIR%^)...
      %PIP_COMMON% --no-index --find-links "%WHEEL_DIR%" -r requirements.txt
      if errorlevel 1 (
        echo تحذير: فشل التثبيت من الحزم المحلية، سيتم المحاولة عبر الإنترنت.
        %PIP_COMMON% -r requirements.txt
      )
    ) else (
      %PIP_COMMON% -r requirements.txt
    )
    if errorlevel 1 (
      echo تحذير: فشل تثبيت كامل المتطلبات، سيتم المحاولة بقائمة مبسطة.
      if exist requirements_temp.txt (
        if exist "%WHEEL_DIR%\*.whl" (
          %PIP_COMMON% --no-index --find-links "%WHEEL_DIR%" -r requirements_temp.txt
          if errorlevel 1 (
            echo تحذير: فشل التثبيت من الحزم المحلية للقائمة المبسطة، سيتم المحاولة عبر الإنترنت.
            %PIP_COMMON% -r requirements_temp.txt
          )
        ) else (
          %PIP_COMMON% -r requirements_temp.txt
        )
        if errorlevel 1 (
          echo فشل تثبيت المتطلبات المبسطة أيضاً.
          pause
          exit /b 1
        ) else (
          echo تم تثبيت مجموعة أساسية من الحزم ويُمكن تشغيل النظام.
        )
      ) else (
        echo لم يتم العثور على requirements_temp.txt.
        pause
        exit /b 1
      )
    )
  ) else if exist requirements_temp.txt (
    if exist "%WHEEL_DIR%\*.whl" (
      %PIP_COMMON% --no-index --find-links "%WHEEL_DIR%" -r requirements_temp.txt
      if errorlevel 1 (
        echo تحذير: فشل التثبيت من الحزم المحلية، سيتم المحاولة عبر الإنترنت.
        %PIP_COMMON% -r requirements_temp.txt
      )
    ) else (
      %PIP_COMMON% -r requirements_temp.txt
    )
    if errorlevel 1 (
      echo فشل تثبيت المتطلبات المبسطة.
      pause
      exit /b 1
    )
  ) else (
    echo لا يوجد ملف متطلبات.
    pause
    exit /b 1
  )
)

:: إنشاء .env من المثال إذا كان متاحاً
if not exist .env if exist .env.example (
  echo إنشاء ملف .env من .env.example ...
  copy /y .env.example .env >nul
)

:: مجلدات تشغيل أساسية
for %%D in (logs media backups staticfiles) do (
  if not exist "%%D" mkdir "%%D" >nul 2>&1
)

:: تطبيق المهاجرات وجمع الملفات الثابتة
echo تطبيق المهاجرات ...
python manage.py migrate --noinput
if errorlevel 1 (
  echo تم رصد مشكلة في المهاجرات. محاولة دمج التعارضات تلقائياً ...
  python manage.py makemigrations --merge --noinput
  python manage.py makemigrations purchases --merge --noinput
  python manage.py migrate --noinput
  if errorlevel 1 (
    echo حدث خطأ أثناء المهاجرات بعد محاولة الدمج. يرجى المراجعة.
    pause
    exit /b 1
  )
)

echo جمع الملفات الثابتة ...
python manage.py collectstatic --noinput

:: اختبار سريع قبل التشغيل
echo فحص جاهزية النظام ...
python manage.py check
if errorlevel 1 (
  echo يوجد خطأ يمنع التشغيل. راجع الرسائل بالأعلى ثم اضغط أي مفتاح للإغلاق.
  pause
  exit /b 1
)

:: فحص ذاتي شامل مع محاولة الإصلاح التلقائي
echo تشغيل فحص النظام الذاتي وإصلاح المشاكل ...
python manage.py system_self_check --fix
if errorlevel 1 goto :ERR_SELF_CHECK

echo [DBG] After system_self_check

rem اختيار المنفذ: إذا لم يُمرَّر منفذ، استخدم 8000
if not defined FREEPORT set "FREEPORT=8013"
echo استخدام المنفذ %FREEPORT%

rem اختيار نمط التشغيل: محلي أم شبكة
echo.
rem السماح بتمرير نمط التشغيل كوسيط (LOCAL/LAN) واختيار المنفذ كوسيط ثانٍ
set "RUNMODE=1"
set "__arg1=%~1"
set "__arg2=%~2"
if /I "%__arg1%"=="LAN"   set "RUNMODE=2"
if /I "%__arg1%"=="LOCAL" set "RUNMODE=1"
if not "%__arg2%"=="" set "FREEPORT=%__arg2%"
if "%RUNMODE%"=="1" (
  echo الوضع: محلي Local
) else (
  echo الوضع: شبكة LAN
)
echo [DBG] Before branch RUNMODE=%RUNMODE% FREEPORT=%FREEPORT%

if "%RUNMODE%"=="2" goto :LAN

:LOCAL
echo [DBG] Enter LOCAL with ADDR precompute
set "HOST=127.0.0.1"
set "ADDR=%HOST%:%FREEPORT%"
set "PORT=%FREEPORT%"
echo تشغيل الخادم محلياً على http://%ADDR% ...
start "Tony ERP" http://%ADDR%
echo لإيقاف الخادم اضغط Ctrl+C
:RUN_LOCAL_LOOP
echo [DBG] runserver %ADDR%
python manage.py runserver %ADDR%
set "RC=%ERRORLEVEL%"
echo.
echo تم إيقاف الخادم ^(رمز الخروج %RC%^) 
choice /c RP /n /m "R=إعادة تشغيل، P=إنهاء: "
if errorlevel 2 goto :END
goto :RUN_LOCAL_LOOP

:LAN
echo [DBG] Enter LAN
echo تشغيل خادم الشبكة المحلية ...
echo ملاحظة: قد تحتاج لتشغيل هذا الملف كمسؤول لإضافة استثناء جدار الحماية.
set "PORT=%FREEPORT%"
rem محاولة إضافة استثناء جدار الحماية (يتطلب صلاحيات مسؤول، يتجاهل الفشل)
netsh advfirewall firewall add rule name="TonyERP %FREEPORT%" dir=in action=allow protocol=TCP localport=%FREEPORT% profile=any >nul 2>&1
:RUN_LAN_LOOP
echo بدء تشغيل خادم LAN على المنفذ %PORT% ...
set "PORT=%PORT%"
set "NO_INTERACTIVE=1"
python start_network_server.py
set "RC=%ERRORLEVEL%"
echo.
echo تم إنهاء خادم LAN ^(رمز الخروج %RC%^) 
choice /c RP /n /m "R=إعادة تشغيل، P=إنهاء: "
if errorlevel 2 goto :END
goto :RUN_LAN_LOOP

:END
echo.
echo تم إنهاء الجلسة.
pause

:ERR_SELF_CHECK
echo يوجد مشاكل تم الإبلاغ عنها من فحص النظام الذاتي. يرجى المراجعة.
pause
exit /b 1
