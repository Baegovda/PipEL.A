#requires -Version 5.1
<#
.SYNOPSIS
  Line-level hotspots via kernprof / line_profiler (requires pip install kernprof line_profiler).

.DESCRIPTION
  Sets builtins.profile (identity already in main.py when not kernprof).
  Outputs profiling/agent_profile/line_profiler.lprof — load with python -m line_profiler ...

  Does not ship in release EXE workflow; developer machine only.

.EXAMPLE
  pip install kernprof line_profiler
  .\tools\profile_kernprof_pipela.ps1
#>
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$null = Get-Command python -ErrorAction Stop

$ProfDir = Join-Path $RepoRoot 'profiling\agent_profile'
if (-not (Test-Path -LiteralPath $ProfDir)) {
    New-Item -ItemType Directory -Path $ProfDir | Out-Null
}
$Lp = Join-Path $ProfDir 'line_profiler_notify.lprof'
$Ker = Join-Path $RepoRoot 'main.py'

Write-Host "kernprof → $Lp (@builtins.profile on PipelaApplication.notify in dialog_dismiss_on_outside.py)" -ForegroundColor Cyan
Write-Host "Text report: python -m line_profiler -r $Ker $Lp`n" -ForegroundColor DarkGray
& python -m kernprof -l -v -o $Lp $Ker