#requires -Version 5.1
<#
.SYNOPSIS
  Run Pipela under Python cProfile; write profiling/pipela_cprofile_*.stats plus
  profiling/agent_profile/ for a single handoff folder (README.txt + summary.txt + cprofile.stats).

.DESCRIPTION
  Repo root is the parent of this tools/ folder. Uses `python main.py` from that root.
  Before each run, deletes existing `profiling/pipela_cprofile_*.stats` so only the latest remains.
  The timestamp in the filename is taken when profiling ends (cProfile flushes on process exit), not at script start.

.EXAMPLE
  .\tools\profile_pipela.ps1
#>
param()

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$mainPy = Join-Path $RepoRoot 'main.py'
if (-not (Test-Path -LiteralPath $mainPy)) {
    throw "main.py not found at $mainPy"
}

$null = Get-Command python -ErrorAction Stop

$ProfDir = Join-Path $RepoRoot 'profiling'
if (-not (Test-Path -LiteralPath $ProfDir)) {
    New-Item -ItemType Directory -Path $ProfDir | Out-Null
}

Get-ChildItem -LiteralPath $ProfDir -Filter 'pipela_cprofile_*.stats' -File -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue
$Pending = Join-Path $ProfDir 'pipela_cprofile_pending.stats'
if (Test-Path -LiteralPath $Pending) {
    Remove-Item -LiteralPath $Pending -Force -ErrorAction SilentlyContinue
}
$ErrLog = Join-Path $ProfDir 'pipela_cprofile_last_dump_error.txt'
if (Test-Path -LiteralPath $ErrLog) {
    Remove-Item -LiteralPath $ErrLog -Force -ErrorAction SilentlyContinue
}

$Driver = Join-Path $RepoRoot 'tools\cprofile_pipela_driver.py'
if (-not (Test-Path -LiteralPath $Driver)) {
    throw "cprofile_pipela_driver.py not found at $Driver"
}

Write-Host "cProfile: cprofile_pipela_driver.py (dump 실패 시 profiling\pipela_cprofile_last_dump_error.txt) → 종료 시 pipela_cprofile_HHmmss-yyyyMMdd.stats" -ForegroundColor Cyan
& python $Driver
$exit = $LASTEXITCODE

# cProfile는 프로세스 종료 시 flush — 파일명 시각은 기록 종료(저장) 직전
$stamp = Get-Date -Format 'HHmmss-yyyyMMdd'
$stats = Join-Path $ProfDir "pipela_cprofile_$stamp.stats"
$statsPath = $null
if (Test-Path -LiteralPath $Pending) {
    Move-Item -LiteralPath $Pending -Destination $stats -Force
    $statsPath = $stats
} else {
    Write-Warning "cProfile output file missing: $Pending (exit=$exit)"
}

$len = 0
if ($null -ne $statsPath -and (Test-Path -LiteralPath $statsPath)) {
    $len = (Get-Item -LiteralPath $statsPath).Length
}
if ($len -lt 1) {
    if (Test-Path -LiteralPath $ErrLog) {
        Write-Warning "Stats file is empty (exit=$exit). See: $ErrLog"
    } else {
        Write-Warning "Stats file is empty or missing (exit=$exit) — 비정상 종료·권한·백신 등 가능. `tools\cprofile_pipela_driver` 로 재시도."
    }
} elseif ($null -ne $statsPath) {
    Write-Host "Wrote $len bytes → $statsPath" -ForegroundColor DarkGray
}
$AgentDir = Join-Path $ProfDir 'agent_profile'
$ReadmeTpl = Join-Path $RepoRoot 'tools\profiling_agent_profile_README.txt'
$SummaryTool = Join-Path $RepoRoot 'tools\dump_cprofile_summary.py'
if ($null -ne $statsPath -and $len -gt 0) {
    New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
    if (Test-Path -LiteralPath $ReadmeTpl) {
        Copy-Item -LiteralPath $ReadmeTpl -Destination (Join-Path $AgentDir 'README.txt') -Force
    }
    Copy-Item -LiteralPath $statsPath -Destination (Join-Path $AgentDir 'cprofile.stats') -Force
    if (Test-Path -LiteralPath $SummaryTool) {
        Write-Host "Handoff folder → profiling\agent_profile\  (link this folder for the agent)" -ForegroundColor Cyan
        & python $SummaryTool $statsPath
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "dump_cprofile_summary failed (see profiling\agent_profile\cprofile_dump_error.txt if present)"
        }
    }
} elseif ($null -ne $statsPath) {
    Write-Host "Inspect: python -m pstats `"$statsPath`"   then: sort cumulative / stats 40" -ForegroundColor Green
}
