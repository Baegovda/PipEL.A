#requires -Version 5.1
<#
.SYNOPSIS
  Run Pipela under Python cProfile; write timestamped .stats under profiling/.

.DESCRIPTION
  Repo root is the parent of this tools/ folder. Uses `python main.py` from that root.
  Before each run, deletes existing `profiling/pipela_cprofile_*.stats` so only the latest remains.

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

$stamp = Get-Date -Format 'HHmmss-yyyyMMdd'
$stats = Join-Path $ProfDir "pipela_cprofile_$stamp.stats"
Write-Host "cProfile: writing $stats (exit app to finish)" -ForegroundColor Cyan
& python -m cProfile -o $stats main.py
Write-Host "Inspect: python -m pstats `"$stats`"   then: sort cumulative / stats 40" -ForegroundColor Green
