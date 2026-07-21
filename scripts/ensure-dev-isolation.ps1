# AGENT: One-time dual-Cursor / F5 isolation setup for this repo.
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

Write-Host "Pipela dev isolation setup..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "fix-cursor-f5.ps1")
Write-Host ""
Write-Host "Tips:" -ForegroundColor Cyan
Write-Host "  - Open this repo as a single folder per Cursor window."
Write-Host "  - Build: Ctrl+Shift+B or .\scripts\build-release.ps1"
Write-Host "  - Run: F5 (build-and-run, no debugger)"
Write-Host "  - Stuck vcpkg lock: .\scripts\recover-ide-build.ps1"
Write-Host "  - Then: Developer -> Reload Window"
