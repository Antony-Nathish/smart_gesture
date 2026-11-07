
# ============================================
# SMART GESTURE - AUTOMATIC SETUP AND LAUNCHER
# Python 3.12 | PowerShell
# ============================================

$ErrorActionPreference = "Continue"
$Project = (Resolve-Path $PSScriptRoot).Path
$Venv = Join-Path $Project ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$Requirements = Join-Path $Project "requirements.txt"
$Main = Join-Path $Project "main.py"
$Log = Join-Path $Project "setup-install.log"

Clear-Host
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "       SMART GESTURE SETUP MANAGER" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 1. Check project directory
if (!(Test-Path $Project)) {
    Write-Host "ERROR: Project directory not found: $Project" -ForegroundColor Red
    exit 1
}

Set-Location $Project

# 2. Detect Python 3.12
Write-Host "`n[1/7] Detecting Python 3.12..." -ForegroundColor Yellow

$Python312 = $null

$Candidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:ProgramFiles\Python312\python.exe",
    "C:\Python312\python.exe"
)

$Launcher = Get-Command py -ErrorAction SilentlyContinue

if ($Launcher) {
    $Detected = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
    $DetectedPath = "$Detected".Trim()
    if ($LASTEXITCODE -eq 0 -and $DetectedPath -and (Test-Path $DetectedPath)) {
        $Python312 = $DetectedPath
    }
}

if (!$Python312) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        $Candidates += $PythonCommand.Source
    }

    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            $DetectedVersion = & $Candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and "$DetectedVersion".Trim() -eq "3.12") {
                $Python312 = $Candidate
                break
            }
        }
    }
}

if (!$Python312) {
    Write-Host "`nPython 3.12 was not found." -ForegroundColor Red
    Write-Host "Install Python 3.12 from:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/release/python-31210/"
    Write-Host "`nEnable 'Add Python to PATH' during installation."
    exit 1
}

Write-Host "Found: $Python312" -ForegroundColor Green

# 3. Verify Python
Write-Host "`n[2/7] Checking Python version..." -ForegroundColor Yellow

& $Python312 --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "Python execution failed." -ForegroundColor Red
    exit 1
}

# 4. Create or validate virtual environment
Write-Host "`n[3/7] Checking virtual environment..." -ForegroundColor Yellow

$RebuildVenv = $false
if (Test-Path $Venv) {
    if (!(Test-Path $Python)) {
        $RebuildVenv = $true
    } else {
        & $Python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $RebuildVenv = $true
        }
    }
}

if ($RebuildVenv) {
    $VenvItem = Get-Item -LiteralPath $Venv -Force
    if ($VenvItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Host "The .venv path is a link; refusing to replace it automatically." -ForegroundColor Red
        Write-Host "Remove or rename that link, then run run.bat again."
        exit 1
    }
    Write-Host "Replacing an incomplete or incompatible .venv with Python 3.12..." -ForegroundColor Yellow
    try {
        Remove-Item -LiteralPath $Venv -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Host "Could not replace the project .venv: $_" -ForegroundColor Red
        exit 1
    }
}

if (!(Test-Path $Python)) {
    Write-Host "Creating Python 3.12 virtual environment..." -ForegroundColor Cyan

    & $Python312 -m venv $Venv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Virtual environment creation failed." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Existing virtual environment detected." -ForegroundColor Green
}

if (!(Test-Path $Python)) {
    Write-Host "Virtual environment Python missing." -ForegroundColor Red
    exit 1
}

# Verify virtual environment uses Python 3.12
& $Python -c "import sys; print('Virtual environment:', sys.executable); print('Version:', sys.version); raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Virtual environment must use Python 3.12." -ForegroundColor Red
    exit 1
}

# 5. Check pip
Write-Host "`n[4/7] Checking pip..." -ForegroundColor Yellow

& $Python -m pip --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "Repairing pip using ensurepip..." -ForegroundColor Yellow
    & $Python -m ensurepip --upgrade

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Pip repair failed." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Updating pip..." -ForegroundColor Cyan

& $Python -m pip install --upgrade pip

if ($LASTEXITCODE -ne 0) {
    Write-Host "Pip update failed. Checking whether existing pip works..." -ForegroundColor Yellow
    & $Python -m pip --version

    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
}

# 6. Install dependencies
Write-Host "`n[5/7] Installing project dependencies..." -ForegroundColor Yellow

if (!(Test-Path $Requirements)) {
    Write-Host "requirements.txt not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Installation log: $Log" -ForegroundColor Cyan

# Run pip as a separate process so its exit code is reliable.
$Arguments = @(
    "-m", "pip", "install",
    "-r", "`"$Requirements`"",
    "--prefer-binary",
    "--timeout", "120",
    "--retries", "3",
    "--progress-bar", "on"
)

$Process = Start-Process `
    -FilePath $Python `
    -ArgumentList $Arguments `
    -WorkingDirectory $Project `
    -RedirectStandardOutput $Log `
    -RedirectStandardError "$Log.error" `
    -Wait `
    -PassThru `
    -NoNewWindow

$InstallExit = $Process.ExitCode

if (Test-Path $Log) {
    Get-Content $Log
}

if (Test-Path "$Log.error") {
    Get-Content "$Log.error"
}

if ($InstallExit -ne 0) {
    Write-Host "`nDEPENDENCY INSTALLATION FAILED!" -ForegroundColor Red
    Write-Host "Exit code: $InstallExit" -ForegroundColor Red
    Write-Host "Check setup-install.log and setup-install.log.error"
    exit 1
}

Write-Host "Dependencies installed successfully!" -ForegroundColor Green

# 7. Verify dependencies
Write-Host "`n[6/7] Checking installed dependencies..." -ForegroundColor Yellow

& $Python -m pip check

if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependency conflicts detected." -ForegroundColor Red
    exit 1
}

& $Python -c "import tkinter, cv2, mediapipe as mp, numpy, pyautogui; assert hasattr(mp, 'solutions'); print('Tk:', tkinter.TkVersion, '| OpenCV:', cv2.__version__, '| MediaPipe:', mp.__version__, '| NumPy:', numpy.__version__)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Application dependency or Tkinter import check failed." -ForegroundColor Red
    Write-Host "Modify Python 3.12 to include Tcl/Tk, then run run.bat again."
    exit 1
}

# 8. Launch application
Write-Host "`n[7/7] Launching Smart Gesture..." -ForegroundColor Yellow

if (!(Test-Path $Main)) {
    Write-Host "main.py not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "       STARTING SMART GESTURE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

& $Python $Main

Write-Host "`nApplication closed." -ForegroundColor Cyan
