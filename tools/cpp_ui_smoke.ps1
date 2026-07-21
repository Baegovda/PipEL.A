# AGENT: Headless-ish smoke for C++ UI paths (terminal fade, preflight).
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $SkipBuild) {
    & "$Root\scripts\build_cpp_release.bat"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

& $Py "$Root\tools\run_worker_parity_preflight.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Exe = Join-Path $Root "cpp\build\release\src\app\Pipela.exe"
if (-not (Test-Path $Exe)) {
    Write-Error "Pipela.exe not found at $Exe"
    exit 1
}

Write-Host "[cpp_ui_smoke] OK — build + preflight green; manual: F5 splitter/captions/terminal fade"
exit 0
