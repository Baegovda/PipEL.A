@echo off
setlocal
cd /d "%~dp0\.."

if "%VCPKG_ROOT%"=="" (
  echo VCPKG_ROOT is not set.
  exit /b 1
)

pushd cpp
cmake -S . -B build/native -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake" ^
  -DPIPELA_BUILD_QT_APP=OFF -DPIPELA_BUILD_NATIVE_HUD=OFF -DPIPELA_ENABLE_OPENCV=ON
if errorlevel 1 exit /b 1
cmake --build build/native --target pipela_native
if errorlevel 1 exit /b 1
popd

for /r "cpp\build\native" %%F in (pipela_native*.pyd) do (
  copy /Y "%%F" "%~dp0..\pipela_native.pyd" >nul
  echo Installed %%F
  exit /b 0
)
echo pipela_native.pyd not found in build tree
exit /b 1
