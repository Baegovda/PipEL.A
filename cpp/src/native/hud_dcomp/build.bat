@echo off
setlocal
cd /d "%~dp0..\..\..\..\.."
call "%~dp0..\..\..\..\scripts\_ensure_msvc_env.bat"
if errorlevel 1 exit /b 1
set "SRC=%~dp0"
if not exist "%SRC%build" mkdir "%SRC%build"
cmake -S "%SRC%" -B "%SRC%build" -G Ninja -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 exit /b 1
cmake --build "%SRC%build"
exit /b %ERRORLEVEL%
