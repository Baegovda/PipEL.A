# AGENT: Incremental C++ Qt build — sole AI/owner daily build entry (PIPBONG-style).
#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "build-common.ps1")

$paths = Initialize-PipelaBuildPaths -ScriptsDir $PSScriptRoot
Set-Location $paths.RepoRoot

Ensure-MsvcEnvironment
Prepare-IncrementalBuildEnvironment -BuildDir $paths.BuildDir
Ensure-BuildTreeConfigured -Paths $paths
Invoke-CmakeIncrementalBuild -Paths $paths

Write-Host "OK: $($paths.ExePath)" -ForegroundColor Green
exit 0
