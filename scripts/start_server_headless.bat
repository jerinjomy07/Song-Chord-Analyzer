@echo off
cd /d "%~dp0\.."

set "PYTHON_EXE=%USERPROFILE%\AppData\Roaming\StemKit\venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

if not exist "%LOCALAPPDATA%\SongChordAnalyzer" mkdir "%LOCALAPPDATA%\SongChordAnalyzer"

"%PYTHON_EXE%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > "%LOCALAPPDATA%\SongChordAnalyzer\server.log" 2>&1
