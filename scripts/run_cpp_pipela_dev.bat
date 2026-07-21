@echo off
setlocal
cd /d "%~dp0\..\cpp\build\release\src\app"
if not exist "Pipela.exe" (
  echo Pipela.exe not found. Run: scripts\build_cpp_release.bat
  exit /b 1
)
set "PIPELA_DEV_UI=1"
start "" "%CD%\Pipela.exe"
exit /b 0
