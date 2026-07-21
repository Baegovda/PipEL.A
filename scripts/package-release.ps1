#Requires -Version 5.1
# AGENT: PIPBONG naming alias — calls package_cpp_release.bat
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
& (Join-Path $repoRoot "scripts\package_cpp_release.bat")
exit $LASTEXITCODE
