@echo off
REM Run this ONCE to sign in to Google (after placing credentials.json here).
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" setup_google.py
