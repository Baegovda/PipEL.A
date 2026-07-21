# AGENT: Shared incremental C++ build helpers (PIPBONG-style). Dot-source from build-release.ps1 only.
#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Initialize-PipelaBuildPaths {
    param([string]$ScriptsDir = $PSScriptRoot)

    $repoRoot = (Resolve-Path (Join-Path $ScriptsDir "..")).Path
    $cppRoot = Join-Path $repoRoot "cpp"
    $buildDir = Join-Path $cppRoot "build\release"
    $cppNorm = ($cppRoot -replace '\\', '/')

    return [ordered]@{
        RepoRoot           = $repoRoot
        CppSourceDir       = $cppRoot
        CppSourceDirNorm   = $cppNorm
        BuildDir           = $buildDir
        CmakeCache         = Join-Path $buildDir "CMakeCache.txt"
        VcpkgLock          = Join-Path $buildDir "vcpkg_installed\vcpkg\vcpkg-running.lock"
        ExePath            = Join-Path $buildDir "src\app\Pipela.exe"
        ExeCwd             = Join-Path $buildDir "src\app"
        CmakeTarget        = "Pipela"
        CmakePreset        = "release"
        SourceDirCacheKey  = "CMAKE_HOME_DIRECTORY"
        UsesVcpkg          = $true
    }
}

function Ensure-MsvcEnvironment {
    if ($env:PIPELA_MSVC_ENV_READY -eq "1" -and $env:VCINSTALLDIR) {
        return
    }
    $vsInstall = "C:\PROGRA~2\MICROS~2\2022\BUILDT~1"
    $vcvars = Join-Path $vsInstall "VC\Auxiliary\Build\vcvars64.bat"
    if (-not (Test-Path -LiteralPath $vcvars)) {
        throw "MSVC Build Tools not found at $vsInstall (install VS 2022 C++ x64 workload)"
    }
    $envLines = cmd /c "`"$vcvars`" >nul 2>&1 && set"
    foreach ($line in $envLines) {
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { continue }
        Set-Item -Path "Env:$($line.Substring(0, $eq))" -Value $line.Substring($eq + 1)
    }
    $env:PIPELA_MSVC_ENV_READY = "1"
}

function Get-RepoVcpkgLockHolders {
    param(
        [string]$BuildDir
    )
    $buildMarker = (($BuildDir -replace '\\', '/') + '/').ToLowerInvariant()
    $holders = @()
    foreach ($proc in Get-Process cmake, vcpkg -ErrorAction SilentlyContinue) {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -and $cmd.ToLowerInvariant().Contains($buildMarker)) {
                $holders += $proc
            }
        } catch {
            $holders += $proc
        }
    }
    return $holders
}

function Clear-StaleVcpkgLock {
    param([string]$BuildDir)

    $lock = Join-Path $BuildDir "vcpkg_installed\vcpkg\vcpkg-running.lock"
    if (-not (Test-Path -LiteralPath $lock)) {
        return $false
    }
    if (Get-RepoVcpkgLockHolders -BuildDir $BuildDir) {
        return $false
    }
    Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
    Write-Host "Cleared stale vcpkg-running.lock" -ForegroundColor Yellow
    return $true
}

function Clear-StaleVcpkgLocksRecursive {
    param([string]$BuildDir)

    if (Clear-StaleVcpkgLock -BuildDir $BuildDir) {
        return
    }
    $vcpkgAlive = Get-Process -Name "vcpkg" -ErrorAction SilentlyContinue
    if ($vcpkgAlive) {
        return
    }
    Get-ChildItem -Path $BuildDir -Filter "vcpkg-running.lock" -Recurse -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            try {
                Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
                Write-Host "Cleared stale vcpkg lock: $($_.FullName)" -ForegroundColor Yellow
            } catch { }
        }
    if ($env:VCPKG_ROOT -and (Test-Path $env:VCPKG_ROOT)) {
        Get-ChildItem -Path $env:VCPKG_ROOT -Filter "vcpkg-running.lock" -Recurse -Force -ErrorAction SilentlyContinue |
            ForEach-Object {
                try {
                    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
                    Write-Host "Cleared stale vcpkg lock: $($_.FullName)" -ForegroundColor Yellow
                } catch { }
            }
    }
}

function Stop-StuckConfigureProcesses {
    param([switch]$IncludeMsbuild)

    $names = @("Pipela", "cmake", "vcpkg", "ninja", "cl", "link")
    if ($IncludeMsbuild) {
        $names += "msbuild"
    }
    foreach ($name in $names) {
        Stop-Process -Name $name -Force -ErrorAction SilentlyContinue
    }
}

function Wait-ForRepoVcpkgLock {
    param(
        [string]$BuildDir,
        [int]$TimeoutSeconds = 120
    )

    $lock = Join-Path $BuildDir "vcpkg_installed\vcpkg\vcpkg-running.lock"
    if (-not (Test-Path -LiteralPath $lock)) {
        return $true
    }
    if (Clear-StaleVcpkgLock -BuildDir $BuildDir) {
        return $true
    }
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        if (-not (Test-Path -LiteralPath $lock)) {
            return $true
        }
        if (Clear-StaleVcpkgLock -BuildDir $BuildDir) {
            return $true
        }
    }
    Write-Host "Timed out on vcpkg lock. Run .\scripts\recover-ide-build.ps1" -ForegroundColor Red
    return $false
}

function Prepare-IncrementalBuildEnvironment {
    param([string]$BuildDir)

    Clear-StaleVcpkgLocksRecursive -BuildDir $BuildDir
    Stop-Process -Name "Pipela" -Force -ErrorAction SilentlyContinue
    $lock = Join-Path $BuildDir "vcpkg_installed\vcpkg\vcpkg-running.lock"
    if ((Test-Path -LiteralPath $lock) -and -not (Wait-ForRepoVcpkgLock -BuildDir $BuildDir)) {
        exit 1
    }
}

function Ensure-VcpkgRoot {
    if ($env:VCPKG_ROOT -and (Test-Path (Join-Path $env:VCPKG_ROOT "scripts\buildsystems\vcpkg.cmake"))) {
        return
    }
    $candidates = @(
        (Join-Path $env:USERPROFILE "vcpkg"),
        (Join-Path $env:USERPROFILE "source\repos\vcpkg"),
        "C:\vcpkg"
    )
    foreach ($root in $candidates) {
        $toolchain = Join-Path $root "scripts\buildsystems\vcpkg.cmake"
        if (Test-Path -LiteralPath $toolchain) {
            $env:VCPKG_ROOT = ($root -replace '\\', '/')
            Write-Host "Using VCPKG_ROOT=$($env:VCPKG_ROOT)" -ForegroundColor DarkGray
            return
        }
    }
    Write-Host "Set VCPKG_ROOT or run scripts\setup_vcpkg.ps1" -ForegroundColor Red
    exit 1
}

function Test-CMakeCachePathMismatch {
    param(
        [string]$CmakeCache,
        [string]$ExpectedSourceDirNorm,
        [string]$SourceDirCacheKey
    )

    if (-not (Test-Path -LiteralPath $CmakeCache)) {
        return $false
    }
    foreach ($line in Get-Content -LiteralPath $CmakeCache) {
        if ($line -match "^${SourceDirCacheKey}:INTERNAL=(.+)$" -or $line -match "^${SourceDirCacheKey}:STATIC=(.+)$") {
            $cached = $Matches[1].Trim() -replace '\\', '/'
            return $cached -ne $ExpectedSourceDirNorm
        }
    }
    return $false
}

function Ensure-BuildTreeConfigured {
    param(
        [hashtable]$Paths
    )

    if (Test-CMakeCachePathMismatch -CmakeCache $Paths.CmakeCache `
            -ExpectedSourceDirNorm $Paths.CppSourceDirNorm `
            -SourceDirCacheKey $Paths.SourceDirCacheKey) {
        Write-Host "CMake cache path mismatch — removing $($Paths.BuildDir)..." -ForegroundColor Yellow
        Remove-Item -LiteralPath $Paths.BuildDir -Recurse -Force
    }

    if (Test-Path -LiteralPath $Paths.CmakeCache) {
        return
    }

    if ($Paths.UsesVcpkg) {
        Ensure-VcpkgRoot
        if (-not (Wait-ForRepoVcpkgLock -BuildDir $Paths.BuildDir -TimeoutSeconds 300)) {
            exit 1
        }
    }

    Write-Host "First configure only (CMakeCache.txt missing)..." -ForegroundColor Cyan
    Push-Location $Paths.CppSourceDir
    try {
        & cmake --preset $Paths.CmakePreset
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }
}

function Invoke-CmakeIncrementalBuild {
    param(
        [hashtable]$Paths
    )

    if (-not (Test-Path -LiteralPath $Paths.CmakeCache)) {
        throw "Build tree not configured. Run: .\scripts\build-release.ps1"
    }

    Write-Host "Building Release (incremental, target $($Paths.CmakeTarget))..." -ForegroundColor Cyan
    & cmake --build $Paths.BuildDir --config Release --target $Paths.CmakeTarget
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
