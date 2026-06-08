@echo off
REM Double-click this file to start Jarvis.
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" jarvis.py
echo.
echo Jarvis has stopped. Press any key to close this window.
pause >nul
