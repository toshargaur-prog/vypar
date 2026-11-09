@echo off
title VyaparAI OS - Export to USB Flash Drive
cls
echo ======================================================================
echo    VyaparAI OS - Portable USB Data Export Tool
echo ======================================================================
echo.

set TARGET_DIR=%~dp0backups
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%
set BACKUP_FILE=%TARGET_DIR%\vyapar_ai_backup_%TIMESTAMP%.db

echo [+] Copying live database to:
echo     %BACKUP_FILE%

copy /Y "%~dp0vyapar_ai.db" "%BACKUP_FILE%" >nul

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Backup created successfully!
    echo You can copy "%BACKUP_FILE%" or this entire folder
    echo to a USB Pen Drive to run on any other PC.
) else (
    echo.
    echo [WARNING] Could not copy database. Make sure vyapar_ai.db exists.
)

echo.
pause
