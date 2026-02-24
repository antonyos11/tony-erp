@echo off
chcp 65001 >nul 2>&1
title Tony ERP - تشغيل على الشبكة المحلية (LAN)

REM تشغيل خادم Django ليعمل على كل الواجهات (للوصول من الجوال)
set PORT=8000

REM تفعيل البيئة الافتراضية إن وُجدت
if exist ".venv\Scripts\activate.bat" (
	call .venv\Scripts\activate.bat
) else (
	echo تحذير: لم يتم العثور على .venv\Scripts\activate.bat - سيتم استخدام Python الافتراضي في PATH
)

REM محاولة استخراج عنوان LAN لعرض رابط سريع (اختياري)
set "LANIP="
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr IPv4') do (
	set "_raw=%%A"
	setlocal enabledelayedexpansion
	set "_raw=!_raw: =!"
	if not defined LANIP (
		for /f "tokens=1" %%B in ("!_raw!") do (
			endlocal & set "LANIP=%%B"
		)
	) else (
		endlocal
	)
)

if defined LANIP (
	echo رابط الوصول من الموبايل (نفس شبكة Wi‑Fi): http://%LANIP%:%PORT%
) else (
	echo ملاحظة: لم أتمكن من تحديد عنوان LAN تلقائياً. استخدم عنوان جهازك يدوياً.
)

echo.
echo إن لم تتمكن من الوصول من هاتفك: شغّل enable_dev_firewall_rules.bat كمسؤول مرة واحدة.
echo.

echo بدء تشغيل خادم Django على 0.0.0.0:%PORT% ... (Ctrl+C للإيقاف)
python manage.py runserver 0.0.0.0:%PORT%

echo.
echo تم إيقاف الخادم.
pause
