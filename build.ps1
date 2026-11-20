# TriageIQ - end-to-end build (Windows / PowerShell)
# Creates an isolated .venv, installs dependencies, smoke-tests the config,
# builds the knowledge base, and runs the test suite. Safe to re-run.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== TriageIQ end-to-end build ==" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[1/5] Creating virtual environment .venv ..."
    python -m venv .venv
} else {
    Write-Host "[1/5] Virtual environment .venv already exists - reusing it."
}
$py = ".\.venv\Scripts\python.exe"

Write-Host "[2/5] Installing dependencies (requirements.txt) ..."
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -r requirements.txt

Write-Host "[3/5] Configuration smoke test (test.py) ..."
& $py test.py

Write-Host "[4/5] Building the knowledge base (data_ingestion.py) ..."
& $py data_ingestion.py

Write-Host "[5/5] Running the test suite (pytest) ..."
& $py -m pytest -q

Write-Host ""
Write-Host "BUILD OK - TriageIQ is ready." -ForegroundColor Green
Write-Host "Run it with:  .\.venv\Scripts\python.exe app.py"
Write-Host "Then open:    http://127.0.0.1:8080"
