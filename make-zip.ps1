# Creates Marksheet.zip in this folder: the project WITHOUT the machine-specific folders
# (backend\.venv and frontend\node_modules, ~420 MB, rebuilt by setup.bat on the new laptop).
#   .\make-zip.ps1               -> excludes backend\.env (your API key stays private)
#   .\make-zip.ps1 -IncludeKey   -> includes backend\.env (no key prompt on the new laptop)
param([switch]$IncludeKey)
$root = $PSScriptRoot
$stage = Join-Path $root ".pack\Ai_Project_Test"
$zip = Join-Path $root "Marksheet.zip"

Remove-Item -Recurse -Force (Join-Path $root ".pack") -ErrorAction SilentlyContinue
Remove-Item -Force $zip -ErrorAction SilentlyContinue

$excludeFiles = @("*.zip")
if (-not $IncludeKey) { $excludeFiles += ".env" }
robocopy $root $stage /E /NFL /NDL /NJH /NJS /NP /XD ".venv" "node_modules" "__pycache__" ".pack" /XF $excludeFiles | Out-Null

Compress-Archive -Path $stage -DestinationPath $zip
Remove-Item -Recurse -Force (Join-Path $root ".pack")
$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Created $zip ($mb MB)" -ForegroundColor Green
if (-not $IncludeKey) { Write-Host "backend\.env was left out - setup.bat will ask for the API key on the new laptop." }
