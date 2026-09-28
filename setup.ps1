# One-time installer for a fresh laptop. Safe to re-run: it repairs or skips what is already done.
# Needs Python 3.11+ and Node.js 20.19+ installed first (see SETUP.md).
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }

# ---- 1. Python -------------------------------------------------------------
Step "Checking Python"
$py = $null
foreach ($cand in @("python", "py")) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) {
        $v = & $cand -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -and [version]$v -ge [version]"3.11") { $py = $cand; break }
    }
}
if (-not $py) { Fail "Python 3.11 or newer not found. Install it from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'." }
Write-Host "Python $(& $py --version) OK"

# ---- 2. Node.js ------------------------------------------------------------
Step "Checking Node.js"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail "Node.js not found. Install the LTS version from https://nodejs.org/ then open a NEW terminal." }
$nv = (node -v).TrimStart("v")
if ([version]$nv -lt [version]"20.19.0") { Fail "Node.js $nv is too old. Install the LTS version (22 or newer) from https://nodejs.org/." }
Write-Host "Node.js v$nv OK"

# ---- 3. Backend virtual environment ----------------------------------------
Step "Setting up the Python environment (backend\.venv)"
$venvPy = Join-Path $root "backend\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    & $venvPy -c "import sys" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Existing .venv was copied from another PC and is broken - recreating it."
        Remove-Item -Recurse -Force (Join-Path $root "backend\.venv")
    }
}
if (-not (Test-Path $venvPy)) { & $py -m venv (Join-Path $root "backend\.venv") }
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r (Join-Path $root "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "pip install failed (check your internet connection)." }

# ---- 4. Frontend -----------------------------------------------------------
Step "Installing frontend packages (npm)"
Push-Location (Join-Path $root "frontend")
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { npm install }
    if ($LASTEXITCODE -ne 0) { Fail "npm install failed." }
    Step "Building the web interface"
    npm run build
    if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed." }
} finally { Pop-Location }

# ---- 5. API key --------------------------------------------------------------
Step "Configuring the Gemini API key (backend\.env)"
$envFile = Join-Path $root "backend\.env"
if (-not (Test-Path $envFile)) { Copy-Item (Join-Path $root "backend\.env.example") $envFile }
$content = Get-Content $envFile -Raw
if ($content -match "GEMINI_API_KEY=paste-your-key-here" -or $content -notmatch "GEMINI_API_KEY=\S+") {
    Write-Host "Get a free key at https://aistudio.google.com/apikey"
    $key = Read-Host "Paste your Gemini API key"
    if (-not $key.Trim()) { Fail "No key entered. Re-run setup, or edit backend\.env by hand." }
    $content = $content -replace "GEMINI_API_KEY=.*", "GEMINI_API_KEY=$($key.Trim())"
    Set-Content -Path $envFile -Value $content -NoNewline -Encoding utf8
} else { Write-Host "Key already present." }

# ---- 6. Smoke test -----------------------------------------------------------
Step "Testing the installation"
Push-Location (Join-Path $root "backend")
try {
    & $venvPy -c "import fastapi, sqlmodel, google.genai, pymupdf, cv2, rapidfuzz; from app.main import app; print('Backend imports OK')"
    if ($LASTEXITCODE -ne 0) { Fail "Backend import test failed." }
    & $venvPy -c "from google import genai; from app.config import get_settings; c = genai.Client(api_key=get_settings().gemini_api_key); n = sum(1 for _ in c.models.list()); print(f'Gemini key OK ({n} models available)')"
    if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: the API key did not work. Fix GEMINI_API_KEY in backend\.env." -ForegroundColor Yellow }
} finally { Pop-Location }

Write-Host "`nSetup complete. Start the app by double-clicking run.bat (opens http://localhost:8000)." -ForegroundColor Green
