@echo off
setlocal
cd /d "%~dp0\.."

set "EXE=cpp\build\release\src\app\Pipela.exe"
if not exist "%EXE%" (
  set "EXE=cpp\build\cpp-release\src\app\Pipela.exe"
)
if not exist "%EXE%" (
  echo Build release first: scripts\build_cpp_release.bat
  exit /b 1
)

set "PIPELA_PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PIPELA_PY%" set "PIPELA_PY=python"
"%PIPELA_PY%" -c "import json;print(json.load(open('version.json',encoding='utf-8'))['version'])" > dist\_cpp_pkg_ver.txt
set /p VER=<dist\_cpp_pkg_ver.txt
del dist\_cpp_pkg_ver.txt 2>nul
set OUT=dist\Pipela-cpp-%VER%-win64.zip
if not exist dist mkdir dist

set STAGE=dist\cpp_release_stage
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%"
copy /y "%EXE%" "%STAGE%\Pipela.exe" >nul

set "EXEDIR=%EXE%\.."
if exist "%EXEDIR%\pipela_input_hooks.dll" (
  copy /y "%EXEDIR%\pipela_input_hooks.dll" "%STAGE%\" >nul
)
if exist "%EXEDIR%\cursor_hud_dcomp.dll" (
  copy /y "%EXEDIR%\cursor_hud_dcomp.dll" "%STAGE%\" >nul
)
if exist "%EXEDIR%\platforms" (
  xcopy /E /I /Y "%EXEDIR%\platforms" "%STAGE%\platforms" >nul
)
if exist "%EXEDIR%\styles" (
  xcopy /E /I /Y "%EXEDIR%\styles" "%STAGE%\styles" >nul
)
if exist "%EXEDIR%\imageformats" (
  xcopy /E /I /Y "%EXEDIR%\imageformats" "%STAGE%\imageformats" >nul
)

powershell -NoProfile -Command "Compress-Archive -Path '%STAGE%\*' -DestinationPath '%OUT%' -Force"
echo Wrote %OUT%
exit /b 0
