@echo off
title Stop Song Chord Analyzer Server
echo ========================================================
echo   Stopping Song Chord Analyzer Background Server
echo ========================================================
echo.

echo Terminating server on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Killing PID %%a...
    taskkill /F /PID %%a 2>nul
)

echo Terminating any lingering cloudflared processes...
taskkill /F /IM cloudflared.exe /T 2>nul

echo.
echo Server stopped.
timeout /t 2 /nobreak >nul
