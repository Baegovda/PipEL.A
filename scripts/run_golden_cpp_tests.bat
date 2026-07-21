@echo off
setlocal
cd /d "%~dp0\.."
call "%~dp0_ensure_msvc_env.bat"
if errorlevel 1 exit /b 1
if "%VCPKG_ROOT%"=="" set "VCPKG_ROOT=%USERPROFILE%\vcpkg"
if not exist "cpp\build\native\CMakeCache.txt" (
  echo Run scripts\build_native_core.bat first
  exit /b 1
)
cmake --build cpp\build\native --target pipela_golden_tests
if errorlevel 1 exit /b 1
ctest --test-dir cpp\build\native --output-on-failure
exit /b %ERRORLEVEL%
