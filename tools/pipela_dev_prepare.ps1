# AGENT: Pipela workspace-only dev prep — local .venv under repo root (no global pip).
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvDir = Join-Path $Root ".venv"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
$ReqFile = Join-Path $Root "requirements.txt"
$StampFile = Join-Path $VenvDir ".pipela_requirements.stamp"

function Get-ReqHash {
    if (-not (Test-Path $ReqFile)) {
        throw "requirements.txt not found: $ReqFile"
    }
    return (Get-FileHash -Algorithm SHA256 -Path $ReqFile).Hash
}

if (-not (Test-Path $VenvPy)) {
    Write-Host "[Pipela] Creating local .venv (workspace-only)..." -ForegroundColor Cyan
    $launcher = Get-Command python -ErrorAction SilentlyContinue
    if (-not $launcher) {
        throw "python not found on PATH. Install Python 3.10+ and reopen the terminal."
    }
    & $launcher.Source -m venv $VenvDir
    if (-not (Test-Path $VenvPy)) {
        throw "Failed to create .venv at $VenvDir"
    }
}

$reqHash = Get-ReqHash
$prevHash = $null
if (Test-Path $StampFile) {
    $prevHash = (Get-Content -Path $StampFile -Raw).Trim()
}

if ($prevHash -ne $reqHash) {
    Write-Host "[Pipela] Syncing requirements.txt into .venv ..." -ForegroundColor Cyan
    & $VenvPy -m pip install --upgrade pip wheel | Out-Null
    & $VenvPy -m pip install -r $ReqFile
    if ($LASTEXITCODE -ne 0) {
        throw "pip install -r requirements.txt failed"
    }
    # F5 debugger (workspace venv only)
    & $VenvPy -m pip install debugpy | Out-Null
    Set-Content -Path $StampFile -Value $reqHash -NoNewline -Encoding ascii
    Write-Host "[Pipela] Dependencies ready." -ForegroundColor Green
} else {
    Write-Host "[Pipela] .venv OK (requirements unchanged)." -ForegroundColor DarkGray
}

exit 0
