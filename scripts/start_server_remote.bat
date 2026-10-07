@echo off
setlocal enabledelayedexpansion
title Song Chord Analyzer - Remote Server (Localhost-Bound)

echo ========================================================
echo   Song Chord Analyzer - Remote Mode (Localhost-Bound)
echo ========================================================
echo.

cd /d "%~dp0\.."

echo [INFO] Binding to 127.0.0.1:8000 for secure Cloudflare Tunnel proxying.
echo [INFO] Direct public access to port 8000 is blocked.
echo.

set "PYTHON_EXE=%USERPROFILE%\AppData\Roaming\StemKit\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
