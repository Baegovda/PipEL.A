# AGENT: C++ dev UI smoke — standby chrome checklist (no game required).
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $repo "cpp\build\release\src\app\Pipela.exe"
if (-not (Test-Path $exe)) {
    $exe = Join-Path $repo "cpp\build\cpp-release\src\app\Pipela.exe"
}
if (-not (Test-Path $exe)) {
    Write-Error "Pipela.exe not found. Run scripts\build_cpp_release.bat first."
}
$env:PIPELA_DEV_UI = "1"
Write-Host "[smoke] Launching $exe (PIPELA_DEV_UI=1) — manual: centered control + KC + tabs"
Write-Host "[smoke] Resolution dock debug: set PIPELA_DEBUG_KILL_DOCK=1 then grep [KillDock][debug]"
Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe)
Write-Host "[smoke] OK — verify: action grid labels, standby hint, settings breadcrumb, terminal fade"
