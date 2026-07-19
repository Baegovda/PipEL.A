@echo off
setlocal
cd /d "%~dp0"

if "%VCPKG_ROOT%"=="" (
  echo VCPKG_ROOT is not set. Install vcpkg and set VCPKG_ROOT.
  exit /b 1
)

pushd cpp
cmake --preset dev -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake"
if errorlevel 1 exit /b 1
cmake --build --preset dev
if errorlevel 1 exit /b 1
ctest --test-dir build\dev -C Debug --output-on-failure
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
