@echo off
setlocal
cd /d "%~dp0\.."
echo === Pipela C++ cutover bundle (native pyd + optional Qt exe) ===
call scripts\build_native_core.bat
if errorlevel 1 exit /b 1
if "%PIPELA_SKIP_QT_EXE%"=="1" (
  echo Skipping Qt Pipela.exe ^(PIPELA_SKIP_QT_EXE=1^)
  exit /b 0
)
call scripts\build_cpp_release.bat
exit /b %ERRORLEVEL%
