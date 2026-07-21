# AGENT: Wire workspace F5 to default test task (no debugger). Workspace-scoped only.
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$vscodeDir = Join-Path $repoRoot ".vscode"
if (-not (Test-Path -LiteralPath $vscodeDir)) {
    New-Item -ItemType Directory -Path $vscodeDir | Out-Null
}

$settingsPath = Join-Path $vscodeDir "settings.json"
if (Test-Path -LiteralPath $settingsPath) {
    $raw = Get-Content -LiteralPath $settingsPath -Raw
    if ($raw -notmatch '"pipela\.f5BuildAndRun"') {
        $raw = $raw -replace '(\{\s*\r?\n)', "`$1  `"pipela.f5BuildAndRun`": true,`r`n"
        Set-Content -LiteralPath $settingsPath -Value $raw -Encoding UTF8 -NoNewline
    }
}

$keybindingsPath = Join-Path $vscodeDir "keybindings.json"
@'
[
  {
    "key": "f5",
    "command": "workbench.action.tasks.test",
    "when": "taskCommandsRegistered"
  }
]
'@ | Set-Content -LiteralPath $keybindingsPath -Encoding UTF8

$launchPath = Join-Path $vscodeDir "launch.json"
@'
{
  "version": "0.2.0",
  "configurations": []
}
'@ | Set-Content -LiteralPath $launchPath -Encoding UTF8

Write-Host "F5 wired to Build and Run (test task). pipela.f5BuildAndRun=true." -ForegroundColor Green
Write-Host "Developer: Reload Window" -ForegroundColor DarkGray
