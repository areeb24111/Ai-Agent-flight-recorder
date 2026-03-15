# Start all Agent Flight Recorder services (API, demo agent, workers) and optionally the frontend.
# Backend processes run in the background (no extra windows). Logs go to backend\logs\.
# Run from repo root: .\scripts\start.ps1
# Optional: .\scripts\start.ps1 -IncludeFrontend  (starts dashboard at http://localhost:5173)

param(
    [switch]$IncludeFrontend
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"
$LogDir = Join-Path $Backend "logs"

if (-not (Test-Path $Backend)) {
    Write-Error "Backend folder not found at $Backend. Run this script from the repo root."
}
$Venv = Join-Path $Backend ".venv"
$VenvScripts = Join-Path $Venv "Scripts"
$Python = Join-Path $VenvScripts "python.exe"
$Uvicorn = Join-Path $VenvScripts "uvicorn.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Backend venv not found. Create it: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt (or install deps manually)"
}

# Ensure log directory exists
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# Pass API_KEY from backend\.env to demo agent (FLIGHT_RECORDER_API_KEY)
$EnvFile = Join-Path $Backend ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*API_KEY\s*=\s*(.+)$') {
            $env:FLIGHT_RECORDER_API_KEY = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
}

Write-Host "Starting Agent Flight Recorder stack from $RepoRoot"
Write-Host ""

# API (port 8000) - run hidden, log to files
Start-Process -FilePath $Uvicorn -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $Backend -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "api.out.log") -RedirectStandardError (Join-Path $LogDir "api.err.log") `
    -PassThru | Out-Null
Start-Sleep -Seconds 2
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 3
    Write-Host "[1/5] API started (http://127.0.0.1:8000)"
} catch {
    Write-Host "[1/5] API health check failed. Check backend\logs\api.err.log for errors (e.g. port 8000 in use)." -ForegroundColor Yellow
}

# Demo agent (port 8001)
Start-Process -FilePath $Uvicorn -ArgumentList "simple_agent_api:app", "--host", "127.0.0.1", "--port", "8001" `
    -WorkingDirectory $Backend -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "demo_agent.out.log") -RedirectStandardError (Join-Path $LogDir "demo_agent.err.log") `
    -PassThru | Out-Null
Write-Host "[2/5] Demo agent started (http://127.0.0.1:8001)"

# Failure worker
Start-Process -FilePath $Python -ArgumentList "-m", "app.worker_failures" `
    -WorkingDirectory $Backend -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "worker_failures.out.log") -RedirectStandardError (Join-Path $LogDir "worker_failures.err.log") `
    -PassThru | Out-Null
Write-Host "[3/5] Failure worker started"

# Simulation worker
Start-Process -FilePath $Python -ArgumentList "-m", "app.worker_simulations" `
    -WorkingDirectory $Backend -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "worker_simulations.out.log") -RedirectStandardError (Join-Path $LogDir "worker_simulations.err.log") `
    -PassThru | Out-Null
Write-Host "[4/5] Simulation worker started"

if ($IncludeFrontend) {
    if (-not (Test-Path $Frontend)) {
        Write-Warning "Frontend folder not found; skipping dashboard."
    } else {
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            # On Windows, npm is npm.cmd; Start-Process needs cmd.exe to run it
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory $Frontend -WindowStyle Normal -PassThru | Out-Null
            Write-Host "[5/5] Frontend started (http://localhost:5173)"
        } else {
            Write-Warning "npm not found; run 'cd frontend; npm install; npm run dev' manually."
        }
    }
} else {
    Write-Host "[5/5] Frontend skipped (use -IncludeFrontend to start it)"
}

Write-Host ""
Write-Host "Backend is running in the background (no extra windows). Logs: backend\logs\"
Write-Host "Dashboard: http://localhost:5173  |  API: http://127.0.0.1:8000"
Write-Host "To stop: close this window and run: Get-Process -Name python,uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force"
