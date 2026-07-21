#requires -Version 5.1
<#
.SYNOPSIS
  Run Pipela under Scalene (CPU + memory).

.DESCRIPTION
  Requires: pip install scalene
  Writes profiling/agent_profile/scalene.json (same handoff folder as other profile scripts).
  -Html runs the app a second time and writes profiling/agent_profile/scalene.html (browser).

.EXAMPLE
  .\tools\profile_pipela_scalene.ps1
.EXAMPLE
  .\tools\profile_pipela_scalene.ps1 -Html
#>
param(
    [switch] $Html
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$mainPy = Join-Path $RepoRoot 'main.py'
if (-not (Test-Path -LiteralPath $mainPy)) {
    throw "main.py not found at $mainPy"
}

$null = Get-Command python -ErrorAction Stop
$scalene = Get-Command scalene -ErrorAction SilentlyContinue
if ($null -eq $scalene) {
    throw "scalene not found. Install: pip install scalene"
}

$ProfDir = Join-Path $RepoRoot 'profiling'
if (-not (Test-Path -LiteralPath $ProfDir)) {
    New-Item -ItemType Directory -Path $ProfDir | Out-Null
}
$AgentDir = Join-Path $ProfDir 'agent_profile'
New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
$ReadmeTpl = Join-Path $RepoRoot 'tools\profiling_agent_profile_README.txt'
if (Test-Path -LiteralPath $ReadmeTpl) {
    Copy-Item -LiteralPath $ReadmeTpl -Destination (Join-Path $AgentDir 'README.txt') -Force
}

$JsonOut = Join-Path $AgentDir 'scalene.json'
Write-Host "Scalene JSON → profiling\agent_profile\scalene.json" -ForegroundColor Cyan

$scaleneArgs = @(
    '--json',
    '--outfile', $JsonOut,
    $mainPy
)
& scalene @scaleneArgs
$exit = $LASTEXITCODE

if ($Html) {
    $HtmlOut = Join-Path $AgentDir 'scalene.html'
    Write-Host "Scalene HTML (second app run) → profiling\agent_profile\scalene.html" -ForegroundColor Cyan
    $htmlArgs = @(
        '--html',
        '--outfile', $HtmlOut,
        $mainPy
    )
    & scalene @htmlArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Scalene HTML pass failed"
    }
}

Write-Host "Done exit=$exit — link profiling\agent_profile for the agent" -ForegroundColor Green
exit $exit
