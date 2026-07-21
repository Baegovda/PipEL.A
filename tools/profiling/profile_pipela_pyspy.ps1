#requires -Version 5.1
<#
.SYNOPSIS
  Run Pipela under py-spy (sampling). Good for stutter / spike stacks (low overhead).

.DESCRIPTION
  Requires: pip install py-spy
  Writes profiling/agent_profile/ (single handoff folder — link this only):
    - pyspy.speedscope.json  (text JSON)
  Optional SVG (second run or -Svg): pyspy.svg

  Some Windows setups need an elevated shell for py-spy attach; recording a child process
  (`py-spy record -- python ...`) usually works without admin.

.EXAMPLE
  .\tools\profile_pipela_pyspy.ps1
.EXAMPLE
  .\tools\profile_pipela_pyspy.ps1 -Rate 200
#>
param(
    [int] $Rate = 100,
    [switch] $Svg
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$mainPy = Join-Path $RepoRoot 'main.py'
if (-not (Test-Path -LiteralPath $mainPy)) {
    throw "main.py not found at $mainPy"
}

$null = Get-Command python -ErrorAction Stop
$pyspy = Get-Command py-spy -ErrorAction SilentlyContinue
if ($null -eq $pyspy) {
    throw "py-spy not found. Install: pip install py-spy"
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

$JsonOut = Join-Path $AgentDir 'pyspy.speedscope.json'
$SvgOut = Join-Path $AgentDir 'pyspy.svg'

Write-Host "py-spy: rate=$Rate → agent_profile\pyspy.speedscope.json (folder: profiling\agent_profile)" -ForegroundColor Cyan
$argsList = @(
    'record',
    '-o', $JsonOut,
    '--format', 'speedscope',
    '--rate', "$Rate",
    '--subprocesses',
    '--',
    'python',
    $mainPy
)
& py-spy @argsList
$exit = $LASTEXITCODE

if ($Svg) {
    Write-Host "py-spy: second pass → SVG flame graph → $SvgOut" -ForegroundColor Cyan
    $argsSvg = @(
        'record',
        '-o', $SvgOut,
        '--rate', "$Rate",
        '--subprocesses',
        '--',
        'python',
        $mainPy
    )
    & py-spy @argsSvg
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "SVG pass exit code: $LASTEXITCODE"
    }
}

Write-Host "Done exit=$exit — link profiling\agent_profile for the agent (or https://www.speedscope.app/ on pyspy.speedscope.json)" -ForegroundColor Green
exit $exit
