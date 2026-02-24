@echo off
title Tony ERP Print Agent - Setup Instructions
cls
echo.
echo ==============================================================
echo       Tony ERP - Print Agent for Thermal Printers
echo                   Setup Instructions
echo ==============================================================
echo.
echo.
echo   STEP 1: Install Dependencies
echo   -----------------------------------------------------------
echo   Double-click: install_simple.bat
echo   Wait until installation finishes.
echo.
echo.
echo   STEP 2: Run the Print Agent
echo   -----------------------------------------------------------
echo   Double-click: run_windows.bat
echo   You should see: "Ready - Listening on ws://0.0.0.0:9876"
echo   DO NOT close that window!
echo.
echo.
echo   STEP 3: Test Printing
echo   -----------------------------------------------------------
echo   Open your Tony ERP in the browser.
echo   Go to any product barcode page.
echo   You should see: "Connected" (green badge).
echo   Click any print button to test.
echo.
echo.
echo   TROUBLESHOOTING:
echo   -----------------------------------------------------------
echo   1. Open Command Prompt as Administrator
echo   2. Type: cd %CD%
echo   3. Type: pip install websockets pywin32 --user
echo   4. Type: python -m pywin32_postinstall -install
echo   5. Type: python agent_windows.py
echo.
echo.
echo   NOTES:
echo   -----------------------------------------------------------
echo   - Make sure your printer (XPrinter/Zebra) is installed on Windows
echo   - Check: Control Panel ^> Devices and Printers
echo   - Python 3.8+ must be installed
echo   - When installing Python, check "Add Python to PATH"
echo.
echo ==============================================================
echo.
pause
