@echo off
chcp 65001 >nul 2>&1
title Tony ERP - Backup Now
cd /d "%~dp0"
setlocal

if not exist backups mkdir backups >nul 2>&1

set "STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%"
set "STAMP=%STAMP: =0%"
set "OUT=backups\backup_%STAMP%"

echo إنشاء نسخة احتياطية في %OUT% ...
mkdir "%OUT%" >nul 2>&1
copy /y db.sqlite3 "%OUT%\db.sqlite3" >nul 2>&1
robocopy media "%OUT%\media" /E >nul 2>&1
echo تم إنشاء النسخة الاحتياطية: %OUT%
pause
