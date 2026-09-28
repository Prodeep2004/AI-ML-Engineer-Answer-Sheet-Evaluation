# Start Marksheet.
#   .\run.ps1          -> one server: builds the UI if needed, serves everything at http://localhost:8000
#   .\run.ps1 -Dev     -> hot-reload dev mode: API on :8000 + Vite UI on http://localhost:5173 (two windows)
param([switch]$Dev)

$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "Backend venv missing. See README 'Install'."; exit 1 }

if ($Dev) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; & '$py' -m uvicorn app.main:app --reload --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:5173"
    exit 0
}

if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Marksheet is already running - opening http://localhost:8000"
    Start-Process "http://localhost:8000"
    exit 0
}

if (-not (Test-Path "$root\frontend\dist\index.html")) {
    Write-Host "Building UI..."
    Push-Location "$root\frontend"; npm run build; Pop-Location
}
Start-Job { Start-Sleep 3; Start-Process "http://localhost:8000" } | Out-Null
Set-Location "$root\backend"
& $py -m uvicorn app.main:app --port 8000
