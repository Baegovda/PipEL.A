# AGENT: Package C++ zip + create GitHub Release (version bump ship).
#Requires -Version 5.1
param(
    [string]$Notes = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$manifest = Get-Content (Join-Path $repoRoot "version.json") -Raw | ConvertFrom-Json
$ver = $manifest.version
if (-not $ver) {
    Write-Error "version.json missing version field"
    exit 1
}

Write-Host "Packaging Pipela-cpp-$ver-win64.zip ..." -ForegroundColor Cyan
& (Join-Path $repoRoot "scripts\package_cpp_release.bat")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$zip = Join-Path $repoRoot "dist\Pipela-cpp-$ver-win64.zip"
if (-not (Test-Path -LiteralPath $zip)) {
    Write-Error "Missing $zip after package_cpp_release.bat"
    exit 1
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "gh CLI not found. Zip ready: $zip" -ForegroundColor Yellow
    Write-Host "Manual: gh release create v$ver `"$zip`" --repo Baegovda/PipEL.A --title `"v$ver`""
    exit 0
}

$releaseNotes = if ($Notes) { $Notes } else { $manifest.notes }
if (-not $releaseNotes) {
    $releaseNotes = "Pipela $ver"
}

Write-Host "Creating GitHub release v$ver ..." -ForegroundColor Cyan
& gh release create "v$ver" $zip --repo Baegovda/PipEL.A --title "v$ver" --notes $releaseNotes
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Release v$ver published." -ForegroundColor Green
