@echo off
title SmartScan AI - Setup and Launcher
cd /d "%~dp0"
echo ============================================================
echo   SmartScan AI - Setup and Launcher for Team Members
echo ============================================================
echo.

REM Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Remember to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Create virtual environment if missing
if not exist ".venv" (
    echo [1/3] Creating Python virtual environment...
    python -m venv .venv
)

REM Install required libraries
echo [2/3] Installing dependencies (Flask, NumPy, SciPy, scikit-learn)...
".\.venv\Scripts\pip.exe" install -r requirements.txt --quiet

REM Launch the dashboard
echo [3/3] Starting SmartScan AI Dashboard...
echo Opening browser to http://127.0.0.1:5000
start http://127.0.0.1:5000
".\.venv\Scripts\python.exe" -u run.py
pause
