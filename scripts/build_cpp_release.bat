@echo off
setlocal
cd /d "%~dp0\.."

if "%VCPKG_ROOT%"=="" (
  echo Set VCPKG_ROOT to your vcpkg install path.
  exit /b 1
)

pushd cpp
cmake -S . -B build/cpp-release -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake" ^
  -DPIPELA_BUILD_QT_APP=ON -DPIPELA_BUILD_PYBIND=ON -DPIPELA_ENABLE_OPENCV=ON -DPIPELA_BUILD_NATIVE_HUD=ON
if errorlevel 1 exit /b 1
cmake --build build/cpp-release
if errorlevel 1 exit /b 1
cmake --build build/cpp-release --target package
popd
echo.
echo C++ Pipela built. Run: cpp\build\cpp-release\src\ui\Pipela.exe
exit /b 0
