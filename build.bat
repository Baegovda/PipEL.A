@echo off
cd /d "%~dp0"
chcp 65001 > nul
echo ====================================
echo 이터널시티 매크로 EXE 빌드
echo ====================================
echo.

echo [1/3] PyInstaller 설치 확인 중...
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo PyInstaller가 설치되어 있지 않습니다. 설치 중...
    pip install pyinstaller
    if errorlevel 1 (
        echo PyInstaller 설치 실패!
        pause
        exit /b 1
    )
)

echo.
echo [2/3] 필요한 패키지 설치 확인 중...
pip install -r requirements.txt

echo.
echo [3/4] 배포 폴더 빌드 중 (PyInstaller onedir)...
pyinstaller Pipela.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo 빌드 실패!
    if not defined CI if not defined PIPELA_BUILD_NO_PAUSE pause
    exit /b 1
)

echo.
echo [4/4] 릴리스 zip 패키징 중...
call scripts\package_release.bat
if errorlevel 1 (
    echo.
    echo zip 패키징 실패!
    if not defined CI if not defined PIPELA_BUILD_NO_PAUSE pause
    exit /b 1
)

echo.
echo ====================================
echo 빌드 완료!
echo ====================================
echo.
echo 실행: dist\Pipela\Pipela.exe
echo 배포: dist\Pipela-*-win64.zip
echo.
if not defined CI if not defined PIPELA_BUILD_NO_PAUSE pause