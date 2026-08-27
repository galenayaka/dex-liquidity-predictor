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
# 2. Python environment helpers (self-healing venv detection)
# ---------------------------------------------------------------------------

# Returns $true when $Python can import every module in $Modules.
function Test-PythonModules {
    param(
        [string]$Python,
        [string[]]$Modules
    )
    $modList = ($Modules | ForEach-Object { "'$_'" }) -join ", "
    $code = "import importlib.util, sys; missing = [m for m in [$modList] if importlib.util.find_spec(m) is None]; sys.exit(1 if missing else 0)"
    & $Python -c $code 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

# Creates a project venv (if needed), installs its requirements, and returns its python.
function New-PythonEnv {
    param([string]$Name)
    $dir  = Join-Path $root $Name
    $venv = Join-Path $dir ".venv"
    $py   = Join-Path $venv "Scripts\python.exe"
    $pip  = Join-Path $venv "Scripts\pip.exe"

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: 'python' not found on PATH. Install Python 3.11+ first." -ForegroundColor Red
        exit 1
    }
    if (-not (Test-Path $py)) {
        Write-Host "  creating virtualenv for $Name ..." -ForegroundColor Cyan
        $out = python -m venv $venv 2>&1
        $out | ForEach-Object { Write-Host $_ }
        if (-not (Test-Path $py)) {
            Write-Host "ERROR: failed to create virtualenv for $Name." -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "  installing $Name requirements (this can take a minute) ..." -ForegroundColor Cyan
    $out = & $pip install -r (Join-Path $dir "requirements.txt") 2>&1
    $out | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: failed to install requirements for $Name." -ForegroundColor Red
        exit 1
    }
    return $py
}

# Resolve the Python interpreter for a service, repairing/creating a venv as needed.
function Get-ServicePython {
    param(
        [string]$Name,
        [string[]]$Modules
    )
    $dir    = Join-Path $root $Name
    $venvPy = Join-Path $dir ".venv\Scripts\python.exe"

    # 1. Project venv with all dependencies present.
    if ((Test-Path $venvPy) -and (Test-PythonModules $venvPy $Modules)) {
        return $venvPy
    }

    # 2. Project venv exists but is missing packages - repair it.
    if (Test-Path $venvPy) {
        Write-Host "  repairing $Name venv (dependencies missing) ..." -ForegroundColor Cyan
        $out = & (Join-Path $dir ".venv\Scripts\pip.exe") install -r (Join-Path $dir "requirements.txt") 2>&1
        $out | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: failed to repair $Name venv." -ForegroundColor Red
            exit 1
        }
        return $venvPy
    }

    # 3. No venv: fall back to system python only if it already has the deps.
    $sysPy = Get-Command python -ErrorAction SilentlyContinue
    if ($sysPy -and (Test-PythonModules $sysPy.Source $Modules)) {
        return $sysPy.Source
    }

    # 4. Nothing usable - create a fresh venv and install everything.
    return (New-PythonEnv $Name)
}

$backendModules  = @('fastapi', 'uvicorn', 'pymysql', 'sqlalchemy', 'passlib', 'bcrypt', 'web3', 'eth_abi', 'xgboost', 'sklearn', 'numpy', 'pandas', 'joblib', 'websockets', 'httpx', 'dotenv', 'pydantic', 'pydantic_settings', 'email_validator')
$forecastModules = @('fastapi', 'uvicorn', 'pydantic', 'pandas', 'numpy', 'sklearn', 'xgboost', 'joblib', 'yfinance', 'requests', 'xlrd')

# ---------------------------------------------------------------------------
# 3. Optional first-time setup (force a full install + frontend npm install)
# ---------------------------------------------------------------------------
if ($Setup) {
    foreach ($name in @("backend", "crypto-forecast")) {
        New-PythonEnv $name | Out-Null
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
# 4. Launch each service in its own window
# ---------------------------------------------------------------------------
$backendDir  = Join-Path $root "backend"
$forecastDir = Join-Path $root "crypto-forecast"
$frontendDir = Join-Path $root "frontend"

$backendPy  = Get-ServicePython "backend" $backendModules
$forecastPy = Get-ServicePython "crypto-forecast" $forecastModules

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
