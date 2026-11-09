@echo off
title VyaparAI OS - Indian MSME Operating System
cls
echo ======================================================================
echo    VyaparAI OS - Ultra-Lightweight Edition (Runs on any PC)
echo    AI Operating System for Indian MSMEs
echo ======================================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo NOTE: During installation, be sure to CHECK the box:
    echo       "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

:: 2. Prepare the project virtual environment
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo [+] Creating project virtual environment...
    python -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo [+] Installing required packages...
"%VENV_PYTHON%" -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Could not install required packages. Check your internet connection.
    pause
    exit /b 1
)

:: 3. Display startup banner
echo [+] Python detected:
"%VENV_PYTHON%" --version
echo.
echo [+] Memory footprint: ~50-60 MB RAM (Super Light - 0%% heavy background daemons)
echo [+] Database: Embedded SQLite (Zero cloud hosting cost)
echo [+] Starting VyaparAI OS and opening your web browser...
echo.

:: 4. Run application
"%VENV_PYTHON%" "%~dp0run.py"

echo.
echo Server stopped.
pause
