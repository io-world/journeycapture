<#
.SYNOPSIS
    One-shot Windows build script for journeycapture.exe
.PARAMETER SkipTests
    Skip the pytest run before building.
.PARAMETER OpenDist
    Open the dist\ folder in Explorer after a successful build.
#>
param(
    [switch]$SkipTests,
    [switch]$OpenDist
)

Set-StrictMode -Version Latest
# Do NOT set $ErrorActionPreference = 'Stop' — uv writes info to stderr which
# would be treated as a terminating error. Exit codes are checked explicitly.

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host "    ERROR: $msg" -ForegroundColor Red; exit 1 }

# -- 1. Check uv ---------------------------------------------------------------
Step "Checking for uv"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "    uv not found - installing..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    # Refresh PATH for this session
    $env:PATH = [System.Environment]::GetEnvironmentVariable('PATH', 'User') + ';' + $env:PATH
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Fail "uv install succeeded but 'uv' is still not on PATH. Open a new PowerShell and re-run this script."
    }
}
Ok "uv $(uv --version)"

# -- 2. Sync dependencies ------------------------------------------------------
Step "Syncing dependencies (uv sync)"
uv sync
if ($LASTEXITCODE -ne 0) { Fail "uv sync failed." }
Ok "Dependencies up to date."

# -- 3. Run tests ---------------------------------------------------------------
if (-not $SkipTests) {
    Step "Running test suite (uv run pytest -q)"
    uv run pytest -q
    if ($LASTEXITCODE -ne 0) { Fail "Tests failed - aborting build. Use -SkipTests to bypass." }
    Ok "All tests passed."
} else {
    Write-Host "`n    [skipping tests]" -ForegroundColor Yellow
}

# -- 4. Build exe ---------------------------------------------------------------
# Read version straight from pyproject.toml (via Python's tomllib) so it always
# reflects the current source file, even if `uv sync` hasn't reinstalled since a
# version bump.
$Version = uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])"
if (-not $Version) { Fail "Could not read package version." }
$ExeName = "journeycapture-$Version"
Step "Building dist\${ExeName}.exe (PyInstaller)"
# Remove stale spec so PyInstaller always uses our explicit flags
Remove-Item -Path "$Root\${ExeName}.spec" -ErrorAction SilentlyContinue
uv run pyinstaller --onefile --console --name $ExeName --distpath "$Root\dist" --workpath "$Root\build" --specpath "$Root\build" packaging/run.py
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller build failed." }
Ok "Build complete: $Root\dist\${ExeName}.exe"

# -- 5. Copy config if missing --------------------------------------------------
$cfg = "$Root\dist\config.json"
if (-not (Test-Path $cfg)) {
    Step "Copying config.example.json -> dist\config.json"
    Copy-Item "$Root\config.example.json" $cfg
    Write-Host "    Edit dist\config.json and set a real api_key and allowed_ips before running." -ForegroundColor Yellow
} else {
    Ok "dist\config.json already exists - skipping copy."
}

# -- Done -----------------------------------------------------------------------
Write-Host "`n==> Build finished successfully." -ForegroundColor Green
Write-Host "    Run with:  cd dist ; .\${ExeName}.exe" -ForegroundColor White

if ($OpenDist) { Start-Process explorer.exe "$Root\dist" }
