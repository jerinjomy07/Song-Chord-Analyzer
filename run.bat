@echo off
title Song Chord Analyzer
echo ========================================================
echo         STARTING SONG CHORD ANALYZER
echo ========================================================
echo.

set PYTHON_CMD="%APPDATA%\StemKit\venv\Scripts\python.exe"

if exist %PYTHON_CMD% (
    %PYTHON_CMD% run_app.py
) else (
    python run_app.py
)

pause
