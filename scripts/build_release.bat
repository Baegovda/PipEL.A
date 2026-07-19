@echo off
REM AGENT: incremental PyInstaller — default task-close build (no --clean).
cd /d "%~dp0\.."
chcp 65001 > nul

echo [Pipela] incremental EXE build (scripts\build_release.bat)
echo.

pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo Installing pyinstaller...
    pip install pyinstaller
    if errorlevel 1 exit /b 1
)

pyinstaller Pipela.spec
if errorlevel 1 (
    echo.
    echo Incremental build failed. Try full recovery: build.bat
    exit /b 1
)

call scripts\package_release.bat
if errorlevel 1 exit /b 1

echo.
echo OK: dist\Pipela\Pipela.exe
exit /b 0
