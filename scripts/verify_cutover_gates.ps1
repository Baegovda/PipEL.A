# AGENT: Cutover gate smoke (no release) — see docs/cpp_migration/COMPLETE.md
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "=== Pipela cutover gate smoke ===" -ForegroundColor Cyan

$fail = 0

if (-not (Test-Path "pipela_native.pyd")) {
    Write-Host "[FAIL] pipela_native.pyd missing — run scripts\build_native_core.bat" -ForegroundColor Red
    $fail++
} else {
    Write-Host "[OK] pipela_native.pyd present"
}

& .\.venv\Scripts\python.exe tools\run_worker_parity_preflight.py
if ($LASTEXITCODE -ne 0) { $fail++ }

cmd /c scripts\run_golden_cpp_tests.bat
if ($LASTEXITCODE -ne 0) { $fail++ }

& powershell -NoProfile -ExecutionPolicy Bypass -File tools\test_qt_native_daily.ps1
if ($LASTEXITCODE -ne 0) { $fail++ }

Write-Host ""
if ($fail -eq 0) {
    Write-Host "Smoke passed. Manual: WORKER_PARITY_CHECKLIST in-game + S0-S5 UI." -ForegroundColor Green
    exit 0
}
Write-Host "Smoke failed ($fail checks)." -ForegroundColor Red
exit 1
