#requires -Version 5.1
<#
.SYNOPSIS
  One copy-paste — one play — one folder: Scalene JSON (if installed) + cProfile + tracemalloc + frame_timing.

.DESCRIPTION
  Default: ``scalene run -o …\scalene.json main.py --- --profile-agent`` (Scalene ≥ run/view CLI).
  Fallback: py-spy wraps ``python main.py --profile-agent``, else plain Python.

  -CProfileOnly — no Scalene / no py-spy (cProfile + TM + UI timing only).
  -PreferPySpy / -Gui — use py-spy (often works when Scalene breaks Qt tray/window on Windows).

  After quit, @ ``profiling/agent_profile/`` for the agent.

.EXAMPLE
  .\tools\profile_pipela_bundle.ps1

.EXAMPLE
  .\tools\profile_pipela_bundle.ps1 -PreferPySpy

.EXAMPLE
  If control window / tray never appear under Scalene:
  .\tools\profile_pipela_bundle.ps1 -Gui
#>
param(
    [switch] $CProfileOnly,
    [Alias('Gui')]
    [switch] $PreferPySpy
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$null = Get-Command python -ErrorAction Stop

$ProfDir = Join-Path $RepoRoot 'profiling'
$AgentDir = Join-Path $ProfDir 'agent_profile'
if (-not (Test-Path -LiteralPath $ProfDir)) {
    New-Item -ItemType Directory -Path $ProfDir | Out-Null
}
if (-not (Test-Path -LiteralPath $AgentDir)) {
    New-Item -ItemType Directory -Path $AgentDir | Out-Null
}

Get-ChildItem -LiteralPath $AgentDir -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

$ReadMeOwner = Join-Path $PSScriptRoot 'profile_bundle_one_shot_README.txt'
$ReadMeTpl = Join-Path $PSScriptRoot 'profiling_agent_profile_README.txt'
if (Test-Path -LiteralPath $ReadMeOwner) {
    Copy-Item -LiteralPath $ReadMeOwner -Destination (Join-Path $AgentDir 'README.txt') -Force
} elseif (Test-Path -LiteralPath $ReadMeTpl) {
    Copy-Item -LiteralPath $ReadMeTpl -Destination (Join-Path $AgentDir 'README.txt') -Force
}
Set-Content -Path (Join-Path $AgentDir '.pipela_bundle') -Value ''

$env:PIPELA_TRACEMALLOC = '1'
$env:PIPELA_UI_FRAME_TIMING = '1'

$MainPy = Join-Path $RepoRoot 'main.py'
$ScJson = Join-Path $AgentDir 'scalene.json'
$PsJsonOut = Join-Path $AgentDir 'pyspy.speedscope.json'

Write-Host "--- Pipela profiling bundle (one play) --- " -ForegroundColor Cyan
Write-Host "HANDOFF: profiling\agent_profile\" -ForegroundColor Green
Write-Host "Env: PIPELA_TRACEMALLOC=1, PIPELA_UI_FRAME_TIMING=1, --profile-agent on main" -ForegroundColor DarkGray

$scal = Get-Command scalene -ErrorAction SilentlyContinue
$pyspy = Get-Command py-spy -ErrorAction SilentlyContinue
$exitMain = 0

if ($CProfileOnly) {
    Write-Host "CProfileOnly → python main.py --profile-agent" -ForegroundColor Yellow
    & python $MainPy --profile-agent
    $exitMain = $LASTEXITCODE
}
elseif ($PreferPySpy -and $null -ne $pyspy) {
    Write-Host "PreferPySpy/GUI → py-spy → $PsJsonOut" -ForegroundColor Cyan
    $PyExe = (Get-Command python).Source
    $bundleArgs = @(
        'record',
        '-o', $PsJsonOut,
        '--format', 'speedscope',
        '--rate', '100',
        '--subprocesses',
        '--',
        $PyExe,
        $MainPy,
        '--profile-agent'
    )
    & py-spy @bundleArgs
    $exitMain = $LASTEXITCODE
}
elseif ($null -ne $scal) {
    Write-Host "Scalene JSON -> $ScJson (pip install scalene if missing)" -ForegroundColor Cyan
    Write-Host "  If Qt window/tray never appear: re-run with -PreferPySpy or -Gui (Scalene+Qt can conflict on Windows)." -ForegroundColor DarkYellow
    # New CLI: scalene run [-o OUT] script.py --- args-to-script
    & scalene @('run', '-o', $ScJson, $MainPy, '---', '--profile-agent')
    $exitMain = $LASTEXITCODE
}
elseif ($null -ne $pyspy) {
    Write-Warning "scalene missing → py-spy → pip install scalene for bundled CPU+mem JSON"
    Write-Host "py-spy → $PsJsonOut" -ForegroundColor Cyan
    $PyExe = (Get-Command python).Source
    & py-spy @(
        'record', '-o', $PsJsonOut, '--format', 'speedscope', '--rate', '100', '--subprocesses', '--',
        $PyExe, $MainPy, '--profile-agent')
    $exitMain = $LASTEXITCODE
}
else {
    Write-Warning "No scalene/py-spy — cProfile + tracemalloc + frame_timing only"
    & python $MainPy --profile-agent
    $exitMain = $LASTEXITCODE
}

Write-Host "--- Done exit=$exitMain -> @ profiling\agent_profile\ ---" -ForegroundColor Green
exit $exitMain
