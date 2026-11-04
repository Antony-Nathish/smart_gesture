@echo off
setlocal EnableExtensions
title Gesture-Cursor Launcher

REM Always run from the folder containing this batch file.
cd /d "%~dp0"

echo.
echo ==========================================
echo        GESTURE-CURSOR - WINDOWS LAUNCHER
echo ==========================================
echo.

REM Prefer an existing project virtual environment.
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if exist "%VENV_PY%" goto :venv_ready

echo [INFO] No project virtual environment was found.
echo [INFO] Looking for Python 3.12...

set "BASE_PY="

REM First try the Windows Python Launcher.
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%P in ('py -3.12 -c "import sys; print(sys.executable)"') do set "BASE_PY=%%P"
    )
)

REM If the launcher is unavailable, check the python command.
if not defined BASE_PY (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
        if not errorlevel 1 (
            for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)"') do set "BASE_PY=%%P"
        )
    )
)

REM Check common per-user and system-wide Python 3.12 install locations.
if not defined BASE_PY if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "BASE_PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined BASE_PY if exist "%ProgramFiles%\Python312\python.exe" set "BASE_PY=%ProgramFiles%\Python312\python.exe"

if not defined BASE_PY (
    echo [ERROR] Python 3.12 was not found.
    echo Install Python 3.12 (64-bit), then run this file again.
    echo You do not need to uninstall Python 3.13.
    echo.
    pause
    exit /b 1
)

echo [INFO] Using: "%BASE_PY%"
echo [INFO] Creating .venv...
"%BASE_PY%" -m venv "%~dp0.venv"
if errorlevel 1 (
    echo [ERROR] Could not create the virtual environment.
    pause
    exit /b 1
)

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

:venv_ready
if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment Python was not found:
    echo "%VENV_PY%"
    pause
    exit /b 1
)

echo [INFO] Active project interpreter:
"%VENV_PY%" --version
if errorlevel 1 (
    echo [ERROR] The virtual environment Python could not start.
    pause
    exit /b 1
)

if not exist "%~dp0requirements.txt" (
    echo [ERROR] requirements.txt was not found in this project folder.
    pause
    exit /b 1
)

echo.
echo [1/3] Checking pip...
"%VENV_PY%" -m pip --version
if errorlevel 1 (
    echo [INFO] Bootstrapping pip...
    "%VENV_PY%" -m ensurepip --upgrade
    if errorlevel 1 (
        echo [ERROR] pip could not be installed in the virtual environment.
        pause
        exit /b 1
    )
)

echo.
echo [2/3] Installing or checking project dependencies...
echo Missing packages will be installed. Already satisfied packages are kept.
"%VENV_PY%" -m pip install -r "%~dp0requirements.txt" --prefer-binary --timeout 120 --retries 10
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency installation failed.
    echo Check your internet connection and the error shown above.
    echo Then run this file again.
    pause
    exit /b 1
)

echo.
echo [3/3] Checking installed dependencies...
"%VENV_PY%" -m pip check
if errorlevel 1 (
    echo [ERROR] Dependency conflicts were reported.
    pause
    exit /b 1
)

if not exist "%~dp0main.py" (
    echo [ERROR] main.py was not found in the project folder.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Starting Gesture-Cursor...
echo Close the gesture application normally to return here.
echo ==========================================
echo.

"%VENV_PY%" "%~dp0main.py"
set "APP_EXIT=%ERRORLEVEL%"

echo.
if not "%APP_EXIT%"=="0" (
    echo [WARNING] The application exited with code %APP_EXIT%.
    echo Review the error output above.
) else (
    echo [INFO] Gesture-Cursor has closed.
)
echo.
pause
exit /b %APP_EXIT%
