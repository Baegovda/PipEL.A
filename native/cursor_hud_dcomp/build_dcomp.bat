@echo off
setlocal

REM Load VS dev environment (x64 host + target)
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=amd64 -host_arch=amd64

echo AFTER_DEV
cd /d "C:\Users\Revaptor_FX\Pipela"
echo AFTER_CD

REM Ensure MSVC headers/libs are on INCLUDE/LIB (some setups don't populate them)
set VCTOOLS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207
set PATH=%VCTOOLS%\bin\HostX64\x64;%PATH%
set INCLUDE=%VCTOOLS%\include;%INCLUDE%
set LIB=%VCTOOLS%\lib\x64;%LIB%

if exist native\cursor_hud_dcomp\build (
  rmdir /s /q native\cursor_hud_dcomp\build
)
echo AFTER_RMDIR

mkdir native\cursor_hud_dcomp\build
echo AFTER_MKDIR

set CMAKEEXE=C:\Program Files\Python310\Lib\site-packages\cmake\data\bin\cmake.exe
set NINJAEXE=C:/PROGRA~1/Python310/Scripts/ninja.exe
set RCEXE=C:/PROGRA~2/WI3CF2~1/10/bin/100261~1.0/x64/rc.exe
set MTEXE=C:/PROGRA~2/WI3CF2~1/10/bin/100261~1.0/x64/mt.exe

echo CONFIGURE...
"%CMAKEEXE%" -S native\cursor_hud_dcomp -B native\cursor_hud_dcomp\build -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY ^
  -DCMAKE_MAKE_PROGRAM=%NINJAEXE% ^
  -DCMAKE_RC_COMPILER=%RCEXE% ^
  -DCMAKE_MT=%MTEXE%
if errorlevel 1 exit /b 1

echo BUILD...
"%CMAKEEXE%" --build native\cursor_hud_dcomp\build
if errorlevel 1 exit /b 1

echo DONE. DLLs:
dir /s /b native\cursor_hud_dcomp\build\cursor_hud_dcomp.dll

endlocal
