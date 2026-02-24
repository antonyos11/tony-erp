@echo off
title Tony ERP Print Agent - Windows

echo.
echo ==============================================================
echo           Tony ERP - Print Agent v3.0 (Windows)
echo           Supports: Zebra ZPL / XPrinter ESC-POS / A4
echo ==============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please install Python first:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during install
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check websockets
echo [1/3] Checking websockets...
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo      Installing websockets...
    pip install websockets --user
    if errorlevel 1 (
        pip install websockets
    )
)
echo      [OK] websockets ready

echo.
echo [2/3] Checking pywin32...
python -c "import win32print" >nul 2>&1
if errorlevel 1 (
    echo      Installing pywin32...
    pip install pywin32 --user
    if errorlevel 1 (
        pip install pywin32
    )
    echo      Setting up pywin32...
    python -m pywin32_postinstall -install 2>nul
)
echo      [OK] pywin32 ready

echo.
echo [3/3] Detecting printers...
python -c "import win32print; printers = win32print.EnumPrinters(6); print('      Found ' + str(len(printers)) + ' printer(s)')" 2>nul
if errorlevel 1 (
    echo      [WARNING] Could not detect printers
)

echo.
echo ==============================================================
echo   Starting Print Agent...
echo   Listening on: ws://0.0.0.0:9876
echo.
echo   To stop: Press Ctrl+C
echo ==============================================================
echo.

python agent_windows.py

echo.
echo ==============================================================
echo   Print Agent stopped.
echo ==============================================================
pause
