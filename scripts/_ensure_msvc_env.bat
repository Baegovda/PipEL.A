@echo off
if defined PIPELA_MSVC_ENV_READY exit /b 0

rem AGENT: 8.3 path avoids cmd parsing issues with "(x86)" in Program Files.
set "VSINSTALL=C:\PROGRA~2\MICROS~2\2022\BUILDT~1"
if not exist "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" (
  echo [Pipela] MSVC Build Tools not found at %VSINSTALL%
  echo Install VS 2022 Build Tools with the C++ x64/x86 workload.
  exit /b 1
)
call "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if errorlevel 1 (
  echo [Pipela] vcvars64.bat failed: %VSINSTALL%
  exit /b 1
)
set "PIPELA_MSVC_ENV_READY=1"
exit /b 0
