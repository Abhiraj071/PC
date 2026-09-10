@echo off
title ScanShield Offline Server
echo ========================================================
echo Starting ScanShield Packaged Commodity Compliance Platform
echo Running locally and offline on your PC!
echo ========================================================
echo.
echo 1. Access on this PC:
echo    http://localhost:8000
echo.
echo 2. Access on your Mobile Phone:
echo    http://192.168.43.209:8000
echo    (Make sure phone and PC are on the same Wi-Fi or Hotspot)
echo.
echo Press Ctrl+C to stop the server anytime.
echo ========================================================
echo.

cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
