@echo off
REM AGENT: zip dist\Pipela\ folder for GitHub Release (onedir PyInstaller output).
cd /d "%~dp0\.."
chcp 65001 > nul

if not exist "dist\Pipela\Pipela.exe" (
    echo [package_release] Missing dist\Pipela\Pipela.exe — run build.bat or scripts\build_release.bat first.
    exit /b 1
)

for /f "delims=" %%V in ('python -c "from pipela_core.version_info import PIPELA_APP_VERSION; print(PIPELA_APP_VERSION)"') do set "VER=%%V"
if not defined VER (
    echo [package_release] Could not read PIPELA_APP_VERSION.
    exit /b 1
)

set "OUT=dist\Pipela-%VER%-win64.zip"
if exist "%OUT%" del /f /q "%OUT%"

powershell -NoProfile -Command "Compress-Archive -LiteralPath 'dist\Pipela' -DestinationPath '%OUT%' -Force"
if errorlevel 1 (
    echo [package_release] Compress-Archive failed.
    exit /b 1
)

echo.
echo OK: %OUT%
echo Run: dist\Pipela\Pipela.exe
exit /b 0
