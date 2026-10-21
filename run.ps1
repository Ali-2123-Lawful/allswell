# Allswell: one-command run on Windows (PowerShell).
# Usage:  powershell -ExecutionPolicy Bypass -File run.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

Write-Host "Starting Allswell at http://127.0.0.1:8000"
& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
