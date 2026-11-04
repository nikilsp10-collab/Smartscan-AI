@echo off
title SmartScan AI - Push to GitHub
cd /d "%~dp0"
echo ============================================================
echo   SmartScan AI - Pushing to GitHub
echo   Repository: https://github.com/nikilsp10-collab/Smartscan-AI.git
echo ============================================================
echo.
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Project pushed successfully to GitHub!
) else (
    echo [NOTICE] If prompted, sign in through your browser to finish the push.
)
echo.
pause
