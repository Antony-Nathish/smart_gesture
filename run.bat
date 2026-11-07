@echo off
setlocal
title Gesture-Cursor Setup
cd /d "%~dp0"

REM The setup interface is powered by Windows PowerShell, so it can open
REM even when Python is not installed.
set "SETUP=%~dp0setup.ps1"
if not exist "%SETUP%" (
    echo [ERROR] setup.ps1 was not found beside this launcher.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File "%SETUP%"
if errorlevel 1 (
    echo.
    echo Setup exited with an error. See the setup window or messages above.
    pause
)
exit /b
