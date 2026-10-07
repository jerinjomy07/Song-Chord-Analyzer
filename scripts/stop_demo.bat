@echo off
title Stop Song Chord Analyzer Services

echo ========================================================
echo   Stopping Song Chord Analyzer & Cloudflare Tunnel
echo ========================================================
echo.

echo Terminating uvicorn / python processes...
taskkill /F /IM uvicorn.exe /T 2>nul
taskkill /F /FI "WINDOWTITLE eq *Song Chord Analyzer*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq *FastAPI*" /T 2>nul

echo Terminating cloudflared processes...
taskkill /F /IM cloudflared.exe /T 2>nul
taskkill /F /FI "WINDOWTITLE eq *Cloudflare Tunnel*" /T 2>nul

echo.
echo All demo services stopped successfully.
timeout /t 2 /nobreak >nul
