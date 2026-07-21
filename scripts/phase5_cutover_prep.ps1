# AGENT: Phase 5 cutover prep — no version bump; owner runs before ship.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "[Phase5] Automated gates..." -ForegroundColor Cyan
& "$Root\scripts\verify_cutover_gates.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[Phase5] Worker parity preflight..." -ForegroundColor Cyan
& "$Root\.venv\Scripts\python.exe" "$Root\tools\run_worker_parity_preflight.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Manual gates (owner):" -ForegroundColor Yellow
Write-Host "  - docs/cpp_migration/WORKER_PARITY_CHECKLIST.md"
Write-Host "  - docs/cpp_migration/PARITY_RESULTS.md"
Write-Host "  - docs/cpp_migration/COMPLETE.md"
Write-Host ""
Write-Host "When ready: scripts\build_cpp_release.bat + scripts\package_cpp_release.bat"
Write-Host "Cutover steps: docs/cpp_migration/PHASE5_CUTOVER.md"
