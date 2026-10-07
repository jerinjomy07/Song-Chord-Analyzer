@echo off
setlocal enabledelayedexpansion
title Song Chord Analyzer - Local FastAPI Server (LAN Mode)

echo ========================================================
echo   Song Chord Analyzer - Local Server (LAN Mode)
echo ========================================================
echo.

cd /d "%~dp0\.."

:: Find Local LAN IP
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "Persistent"') do (
    set "LAN_IP=%%a"
    goto :ip_found
)
:ip_found

echo [INFO] Detected Laptop LAN IP: %LAN_IP%
echo [INFO] Phone Local URL:        http://%LAN_IP%:8000
echo.
echo Binding to 0.0.0.0:8000 so the Android app can connect via local Wi-Fi.
echo Press CTRL+C to stop the server.
echo.

set "PYTHON_EXE=%USERPROFILE%\AppData\Roaming\StemKit\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
pause
