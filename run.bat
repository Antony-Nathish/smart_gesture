@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ====================================
echo   Gesture-Controlled Mouse
echo ====================================
echo.

REM ── 1. Locate Python ──────────────────────────────────────────────────────
set "PYTHON_EXE=python"
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    echo        Install Python 3.9-3.13 from https://www.python.org/downloads/
    echo        and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

REM ── 2. Create virtual environment if missing ───────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment in .venv ...
    %PYTHON_EXE% -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment.
        echo        Make sure the 'venv' module is available for your Python install.
        echo.
        pause
        exit /b 1
    )
    echo [SETUP] Virtual environment created.
    REM Remove any stale stamp so dependencies are installed fresh
    if exist ".venv_ready" del /f /q ".venv_ready"
)

set "VENV_PYTHON=.venv\Scripts\python.exe"
set "VENV_PIP=.venv\Scripts\pip.exe"

REM ── 3. Activate the virtual environment ───────────────────────────────────
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo.
    echo ERROR: Failed to activate virtual environment.
    echo        Try deleting the .venv folder and re-running this script.
    echo.
    pause
    exit /b 1
)

REM ── 4. Smart dependency install ────────────────────────────────────────────
REM  We write a stamp file ".venv_ready" after a successful install.
REM  We compare its timestamp to requirements.txt; if requirements.txt is
REM  newer the stamp is stale and we reinstall.  This avoids a full pip run
REM  on every launch once the environment is configured.

set "NEED_INSTALL=0"

if not exist ".venv_ready" (
    set "NEED_INSTALL=1"
    echo [SETUP] No installation stamp found -- will install dependencies.
) else (
    REM Check whether requirements.txt is newer than the stamp file.
    REM  xcopy /d copies only if source is newer; redirect output to NUL.
    REM  Exit code 0 = nothing copied (stamp is up-to-date).
    REM  Exit code 1 = requirements.txt is newer (needs reinstall).
    xcopy /d /y /i "requirements.txt" ".venv_ready_check_tmp\" >nul 2>&1
    if errorlevel 1 (
        set "NEED_INSTALL=1"
        echo [SETUP] requirements.txt has changed -- reinstalling dependencies.
    )
    if exist ".venv_ready_check_tmp" rmdir /s /q ".venv_ready_check_tmp" >nul 2>&1
)

if "!NEED_INSTALL!"=="1" (
    REM Upgrade pip silently first
    echo [SETUP] Upgrading pip...
    %VENV_PYTHON% -m pip install --upgrade pip --quiet
    if errorlevel 1 (
        echo WARNING: pip upgrade failed -- continuing with existing pip version.
    )

    if exist "requirements.txt" (
        echo [SETUP] Installing packages from requirements.txt ...
        %VENV_PYTHON% -m pip install -r requirements.txt
    ) else (
        echo [SETUP] requirements.txt not found -- installing core packages ...
        %VENV_PYTHON% -m pip install opencv-python mediapipe pyautogui numpy Pillow keyboard
    )

    if errorlevel 1 (
        echo.
        echo ERROR: Dependency installation failed.
        echo        Check your internet connection and try again.
        echo        If the problem persists, run:
        echo            .venv\Scripts\pip install -r requirements.txt
        echo        to see the full error output.
        echo.
        pause
        exit /b 1
    )

    REM Write the stamp file (its timestamp marks when install last succeeded)
    echo %date% %time% > ".venv_ready"
    echo [SETUP] Dependencies installed successfully.
) else (
    echo [INFO] Dependencies are up-to-date (delete .venv_ready to force reinstall).
)

echo.

REM ── 5. Verify main.py exists ───────────────────────────────────────────────
if not exist "main.py" (
    echo ERROR: main.py was not found in:
    echo        %CD%
    echo        Make sure run.bat is placed in the gesture_mouse\ folder.
    echo.
    pause
    exit /b 1
)

REM ── 6. Launch the application ─────────────────────────────────────────────
echo [INFO] Starting Gesture Mouse...
echo [INFO] Press F8 in the preview window to toggle control.
echo [INFO] Press ESC or Q to quit.
echo.

%VENV_PYTHON% main.py

echo.
echo ====================================
echo   Application exited.
echo ====================================
echo.
pause
endlocal
