@echo off
title Tony ERP Print Agent - Quick Install

echo.
echo ==============================================================
echo       Tony ERP - Print Agent - Quick Install
echo ==============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo.
    echo Download Python from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during install
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

echo Installing dependencies...
echo.

echo [1/3] Installing websockets...
pip install websockets --user
echo.

echo [2/3] Installing pywin32...
pip install pywin32 --user
echo.

echo [3/3] Installing Pillow + Arabic support...
pip install Pillow arabic-reshaper python-bidi --user
echo.

echo Setting up pywin32...
python -m pywin32_postinstall -install 2>nul
echo.

echo ==============================================================
echo   Installation complete!
echo.
echo   Now run: run_windows.bat
echo ==============================================================
pause
