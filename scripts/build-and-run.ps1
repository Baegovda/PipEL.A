# AGENT: Incremental build then launch Pipela.exe (F5 / default test task).
#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "build-common.ps1")
$paths = Initialize-PipelaBuildPaths -ScriptsDir $PSScriptRoot

& (Join-Path $PSScriptRoot "build-release.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $paths.ExePath)) {
    Write-Error "Missing $($paths.ExePath)"
    exit 1
}

# Qt plugins deployed by CMake POST_BUILD next to Pipela.exe — no separate deploy script.
$env:PIPELA_DEV_UI = "1"
Start-Process -FilePath $paths.ExePath -WorkingDirectory $paths.ExeCwd
Write-Host "Started Pipela.exe" -ForegroundColor Green