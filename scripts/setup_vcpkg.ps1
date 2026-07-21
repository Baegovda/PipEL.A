# AGENT: One-shot vcpkg setup for pipela_native.pyd (owner / CI).
param(
    [string]$VcpkgRoot = $(Join-Path $env:USERPROFILE "vcpkg")
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path "$VcpkgRoot\bootstrap-vcpkg.bat")) {
    Write-Host "Cloning vcpkg to $VcpkgRoot ..."
    git clone --depth 1 https://github.com/microsoft/vcpkg.git $VcpkgRoot
}

& "$VcpkgRoot\bootstrap-vcpkg.bat" -disableMetrics
$env:VCPKG_ROOT = $VcpkgRoot
[Environment]::SetEnvironmentVariable("VCPKG_ROOT", $VcpkgRoot, "User")
Write-Host "VCPKG_ROOT=$VcpkgRoot (also set User env)"
Write-Host "Next: .\scripts\build_native_core.bat"
