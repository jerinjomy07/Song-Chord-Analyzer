@echo off
setlocal enabledelayedexpansion
title Cloudflare Tunnel - Song Chord Analyzer

echo ========================================================
echo   Cloudflare Tunnel Launcher (100%% Free HTTPS Endpoint)
echo ========================================================
echo.

cd /d "%~dp0\.."

set "CF_EXE=%~dp0..\tools\cloudflared.exe"
if not exist "%CF_EXE%" (
    where cloudflared >nul 2>nul
    if %errorlevel% equ 0 (
        set "CF_EXE=cloudflared"
    ) else (
        echo [ERROR] cloudflared.exe not found in tools\ or PATH.
        echo Please ensure tools\cloudflared.exe exists.
        pause
        exit /b 1
    )
)

echo [INFO] Starting Cloudflare Tunnel proxying http://127.0.0.1:8000 ...
echo [INFO] Look for the URL ending with '.trycloudflare.com' below.
echo [INFO] Copy that HTTPS URL into the Android App -> Settings -> Remote URL!
echo.
echo ============================================================================

"%CF_EXE%" tunnel --url http://127.0.0.1:8000
pause
