<#
  DEX Liquidity Predictor — one-command launcher (Windows PowerShell).

  Starts all three services, each in its own window:
    - backend          FastAPI  :8000
    - crypto-forecast  FastAPI  :8100
    - frontend         Next.js  :3000

  Usage:
    # first time only (creates venvs + installs all dependencies)
    powershell -ExecutionPolicy Bypass -File .\start-all.ps1 -Setup

    # every time after that
    powershell -ExecutionPolicy Bypass -File .\start-all.ps1

  Stop a service by closing its window (or Ctrl+C in it).
#>

param(
    [switch]$Setup
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Refresh PATH so newly installed tools (node/npm) are visible in this session
# and inherited by the service windows we spawn.
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

Write-Host ""
Write-Host "=== DEX Liquidity Predictor launcher ===" -ForegroundColor Cyan
Write-Host "root: $root"
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Create env files from examples if they don't exist yet
# ---------------------------------------------------------------------------
$envs = @(
    @{ Dir = "backend";         File = ".env" },
    @{ Dir = "crypto-forecast"; File = ".env" },
    @{ Dir = "frontend";        File = ".env.local" }
)

foreach ($e in $envs) {
    $dir     = Join-Path $root $e.Dir
    $target  = Join-Path $dir $e.File
    $example = Join-Path $dir ".env.example"
    if (-not (Test-Path $target)) {
        if (Test-Path $example) {
            Copy-Item $example $target
            Write-Host ("  copied {0}\.env.example -> {0}\{1}" -f $e.Dir, $e.File)
        }
        else {
            Write-Host ("  warning: no .env.example found in {0}" -f $e.Dir) -ForegroundColor Yellow
        }
    }
}
Write-Host ""

# ---------------------------------------------------------------------------
# 2. Optional first-time setup (venvs + pip install + npm install)
# ---------------------------------------------------------------------------
if ($Setup) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: 'python' not found on PATH. Install Python 3.11+ first." -ForegroundColor Red
        exit 1
    }

    foreach ($name in @("backend", "crypto-forecast")) {
        $dir  = Join-Path $root $name
        $venv = Join-Path $dir ".venv"
        $py   = Join-Path $venv "Scripts\python.exe"
        $pip  = Join-Path $venv "Scripts\pip.exe"

        if (-not (Test-Path $py)) {
            Write-Host "  creating virtualenv in $name ..." -ForegroundColor Cyan
            python -m venv $venv
        }
        Write-Host "  installing $name requirements (this can take a minute) ..." -ForegroundColor Cyan
        & $pip install -r (Join-Path $dir "requirements.txt")
    }

    Write-Host "  installing frontend dependencies ..." -ForegroundColor Cyan
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: Node.js is not installed. Install it from https://nodejs.org first." -ForegroundColor Red
        exit 1
    }
    Push-Location (Join-Path $root "frontend")
    npm.cmd install
    Pop-Location
    Write-Host ""
}

# ---------------------------------------------------------------------------
# 3. Launch each service in its own window
# ---------------------------------------------------------------------------
$backendDir  = Join-Path $root "backend"
$forecastDir = Join-Path $root "crypto-forecast"
$frontendDir = Join-Path $root "frontend"

# Prefer each project's venv; fall back to system python.
$backendPy  = Join-Path $backendDir ".venv\Scripts\python.exe"
$forecastPy = Join-Path $forecastDir ".venv\Scripts\python.exe"
if (-not (Test-Path $backendPy))  { $backendPy  = "python" }
if (-not (Test-Path $forecastPy)) { $forecastPy = "python" }

function Start-Window {
    param(
        [string]$Title,
        [string]$WorkDir,
        [string]$Command
    )
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    Start-Process powershell `
        -WorkingDirectory $WorkDir `
        -ArgumentList @("-NoExit", "-NoProfile", "-EncodedCommand", $encoded) | Out-Null
    Write-Host ("  started {0}" -f $Title) -ForegroundColor Green
}

# Build child commands. `$Host` stays literal so it is set inside the child window.
$backendCmd  = "`$Host.UI.RawUI.WindowTitle='DEX backend :8000'; & '$backendPy' -m uvicorn app.main:app --reload --port 8000"
$forecastCmd = "`$Host.UI.RawUI.WindowTitle='Crypto forecast :8100'; & '$forecastPy' -m uvicorn main:app --host 127.0.0.1 --port 8100"
$frontendCmd = "`$Host.UI.RawUI.WindowTitle='Dashboard :3000'; npm.cmd run dev"

Start-Window -Title "DEX backend :8000"     -WorkDir $backendDir  -Command $backendCmd
Start-Window -Title "Crypto forecast :8100" -WorkDir $forecastDir -Command $forecastCmd
Start-Window -Title "Dashboard :3000"       -WorkDir $frontendDir -Command $frontendCmd

Write-Host ""
Write-Host "All three services are starting in separate windows." -ForegroundColor Cyan
Write-Host "  Dashboard:   http://localhost:3000" -ForegroundColor White
Write-Host "  Backend API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Forecast:    http://localhost:8100/docs" -ForegroundColor White
Write-Host ""
Write-Host "Tip: close a service window (or press Ctrl+C inside it) to stop it." -ForegroundColor DarkGray
