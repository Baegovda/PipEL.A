@echo off
setlocal
cd /d "%~dp0\.."

if not exist "cpp\build\release\Pipela.exe" (
  echo Build release first: build_cpp.bat with release preset
  exit /b 1
)

for /f "delims=" %%V in ('python -c "import json;print(json.load(open('version.json'))['version'])"') do set VER=%%V
set OUT=dist\Pipela-cpp-%VER%-win64.zip
if not exist dist mkdir dist
powershell -NoProfile -Command "Compress-Archive -Path 'cpp\build\release\*' -DestinationPath '%OUT%' -Force"
echo Wrote %OUT%
