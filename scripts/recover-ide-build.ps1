# AGENT: Recover from stuck cmake/vcpkg configure or IDE CMake Tools conflicts.
#Requires -Version 5.1
param([switch]$KillGlobalBuildProcesses)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "build-common.ps1")
$paths = Initialize-PipelaBuildPaths -ScriptsDir $PSScriptRoot
Set-Location $paths.RepoRoot

Write-Host "Recovering IDE build workflow..." -ForegroundColor Cyan
if ($KillGlobalBuildProcesses) {
    Stop-StuckConfigureProcesses -IncludeMsbuild
    Start-Sleep -Milliseconds 500
} else {
    Stop-StuckConfigureProcesses
}

Clear-StaleVcpkgLocksRecursive -BuildDir $paths.BuildDir

foreach ($rel in @(".vscode\settings.json", ".vscode\tasks.json", ".vscode\launch.json", ".vscode\keybindings.json")) {
    if (Test-Path -LiteralPath $rel) {
        git checkout -- $rel 2>$null
    }
}

& (Join-Path $PSScriptRoot "fix-cursor-f5.ps1") 2>$null

Write-Host "Developer: Reload Window, then Ctrl+Shift+B or .\scripts\build-release.ps1" -ForegroundColor Green
Write-Host "If build tree is corrupt: delete cpp\build\release and run build-release.ps1 once." -ForegroundColor DarkGray
