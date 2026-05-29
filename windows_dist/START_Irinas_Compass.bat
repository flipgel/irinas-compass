@echo off
title Irina's Compass
cd /d "%~dp0"

echo ==========================================
echo    Irina's Compass - Starting up...
echo ==========================================

if not exist venv\Scripts\activate.bat (
    echo First run: creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Python not found or not in PATH.
        echo Please install Python from https://python.org
        echo Make sure to check "Add Python to PATH" during install.
        echo.
        pause
        exit /b 1
    )
    echo Installing dependencies (one-time)...
    call venv\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Starting Irina's Compass...
echo Your browser will open automatically.
echo.

streamlit run app.py --server.headless true

pause
