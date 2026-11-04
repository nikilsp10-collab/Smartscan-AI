@echo off
title SmartScan AI - Electronic Warfare Dashboard
cd /d "%~dp0"
echo ============================================================
echo   Starting SmartScan AI Tactical Operations Dashboard...
echo ============================================================
echo   Opening browser to http://127.0.0.1:5000
start http://127.0.0.1:5000
".\.venv\Scripts\python.exe" -u run.py
pause
