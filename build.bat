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
echo [3/3] EXE 파일 빌드 중...
pyinstaller Pipela.spec --clean

if errorlevel 1 (
    echo.
    echo 빌드 실패!
    pause
    exit /b 1
)

echo.
echo ====================================
echo 빌드 완료!
echo ====================================
echo.
echo EXE 파일 위치: dist\Pipela.exe
echo.
echo 이제 dist 폴더의 Pipela.exe를 실행하세요.
echo.
pause