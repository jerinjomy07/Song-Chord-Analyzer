@echo off
setlocal enabledelayedexpansion
title Song Chord Analyzer - Dual Mode Demo Launcher

echo ========================================================
echo   Song Chord Analyzer - Dual Mode Launcher
echo   (Both Local LAN and Remote Internet Available)
echo ========================================================
echo.

cd /d "%~dp0\.."

:: Find Local LAN IP
for /f "tokens=4" %%a in ('route print ^| findstr 0.0.0.0 ^| findstr /v "Persistent"') do (
    set "LAN_IP=%%a"
    goto :ip_found
)
:ip_found

echo [1/2] Launching FastAPI MIR Engine Server...
echo       Local LAN Endpoint: http://%LAN_IP%:8000
echo.

start "FastAPI MIR Server" "%~dp0start_server_local.bat"

:: Brief wait for server to bind
timeout /t 3 /nobreak >nul

echo [2/2] Launching Cloudflare Tunnel for Remote Internet Access...
echo.

start "Cloudflare Tunnel" "%~dp0start_tunnel.bat"

echo ========================================================
echo   Dual Mode Services are RUNNING!
echo ========================================================
echo.
echo For LOCAL MODE:  Set App Settings to http://%LAN_IP%:8000
echo For REMOTE MODE: Set App Settings to the HTTPS URL shown
echo                  in the Cloudflare Tunnel window.
echo.
echo To stop all services, run: scripts\stop_demo.bat
echo.
pause
