@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

call "%~dp0_ensure_msvc_env.bat"
if errorlevel 1 exit /b 1

if "%VCPKG_ROOT%"=="" (
  if exist "%USERPROFILE%\vcpkg\scripts\buildsystems\vcpkg.cmake" (
    set "VCPKG_ROOT=%USERPROFILE%\vcpkg"
  )
)

if "%VCPKG_ROOT%"=="" (
  echo VCPKG_ROOT is not set. Run: powershell -File scripts\setup_vcpkg.ps1
  exit /b 1
)

set "PIPELA_PY_EXE=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PIPELA_PY_EXE%" (
  echo Workspace venv not found: %PIPELA_PY_EXE%
  echo Run: powershell -File tools\pipela_dev_prepare.ps1
  exit /b 1
)
set "PIPELA_PY_PATHS=%TEMP%\pipela_py_paths.txt"
"%PIPELA_PY_EXE%" "%~dp0..\tools\resolve_python_dev_paths.py" > "%PIPELA_PY_PATHS%"
if errorlevel 1 exit /b 1
set "PIPELA_PY_INCLUDE="
set "PIPELA_PY_LIB="
set "LINE_N=0"
for /f "usebackq delims=" %%L in ("%PIPELA_PY_PATHS%") do (
  set /a LINE_N+=1
  if !LINE_N!==1 set "PIPELA_PY_INCLUDE=%%L"
  if !LINE_N!==2 set "PIPELA_PY_LIB=%%L"
)
if not defined PIPELA_PY_INCLUDE (
  echo Failed to resolve Python include path
  exit /b 1
)
if not defined PIPELA_PY_LIB (
  echo Failed to resolve Python library path
  exit /b 1
)

pushd cpp
if exist vcpkg.json.minimal.bak del vcpkg.json.minimal.bak
copy /Y vcpkg.json vcpkg.json.minimal.bak >nul
cmake -S . -B build/native -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake" ^
  -DPIPELA_BUILD_QT_APP=OFF -DPIPELA_BUILD_NATIVE_HUD=OFF -DPIPELA_ENABLE_OPENCV=ON ^
  -DPYBIND11_FINDPYTHON=ON ^
  -DPython_EXECUTABLE="%PIPELA_PY_EXE%" ^
  -DPython_INCLUDE_DIR="%PIPELA_PY_INCLUDE%" ^
  -DPython_LIBRARY="%PIPELA_PY_LIB%"
if errorlevel 1 exit /b 1
cmake --build build/native --target pipela_native
if errorlevel 1 exit /b 1
popd

for /r "cpp\build\native" %%F in (pipela_native*.pyd) do (
  copy /Y "%%F" "%~dp0..\pipela_native.pyd" >nul
  echo Installed %%F
  for %%D in ("%%~dpF*.dll") do (
    copy /Y "%%D" "%~dp0..\" >nul
    echo Installed %%~nxD
  )
  exit /b 0
)
echo pipela_native.pyd not found in build tree
exit /b 1
