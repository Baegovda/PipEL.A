# AGENT: Daily smoke for PIPELA_QT_NATIVE=1 — verifies C++ Pipela.exe path (no GUI hang).
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== PIPELA_QT_NATIVE daily smoke ===" -ForegroundColor Cyan

$candidates = @(
    "cpp\build\release\src\app\Pipela.exe",
    "cpp\build\cpp-release\src\app\Pipela.exe"
)

$exe = $null
foreach ($c in $candidates) {
    if (Test-Path $c) {
        $exe = (Resolve-Path $c).Path
        break
    }
}

if (-not $exe) {
    Write-Host "[SKIP] C++ Pipela.exe not built — run scripts\build_cpp_release.bat once" -ForegroundColor Yellow
    Write-Host "       F5 with launch 'Pipela: C++ Qt' falls back to Python Qt." -ForegroundColor Yellow
    exit 0
}

Write-Host "[OK] Found $exe"
$env:PIPELA_QT_NATIVE = "1"
& .\.venv\Scripts\python.exe -c @"
import os, subprocess, sys
root = os.path.dirname(os.path.abspath('main.py'))
candidates = [
    os.path.join(root, 'cpp', 'build', 'release', 'src', 'app', 'Pipela.exe'),
    os.path.join(root, 'cpp', 'build', 'cpp-release', 'src', 'app', 'Pipela.exe'),
]
for exe in candidates:
    if os.path.isfile(exe):
        print('[OK] main.py would launch:', exe)
        sys.exit(0)
print('[FAIL] exe path mismatch')
sys.exit(1)
"@

if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "Daily smoke passed. Launch: F5 config 'Pipela: C++ Qt (PIPELA_QT_NATIVE)'" -ForegroundColor Green
exit 0
