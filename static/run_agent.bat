@echo off
title Tony ERP Print Agent
cd /d "%~dp0"

echo.
echo ========================================
echo   Tony ERP - Print Agent
echo ========================================
echo   Directory: %cd%
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b
)

if not exist "%~dp0print_agent.py" (
    echo [ERROR] print_agent.py not found in this folder!
    echo Make sure run_agent.bat and print_agent.py are in the same folder.
    pause
    exit /b
)

echo [1/3] Checking Python version...
python --version
echo.

echo [2/3] Installing websockets library...
python -m pip install --upgrade websockets
echo.

echo [3/3] Installing pywin32 (optional, for better printing)...
python -m pip install pywin32 2>nul
if errorlevel 1 (
    echo [NOTE] pywin32 not available - will use fallback printing method
)
echo.

echo ========================================
echo   Starting Print Agent...
echo ========================================
echo.
python "%~dp0print_agent.py"

echo.
echo Print Agent stopped.
pause
