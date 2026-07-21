@echo off
setlocal
rem AGENT: Legacy name — same as build-release.ps1 (incremental; configure only if CMakeCache missing).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-release.ps1"
exit /b %errorlevel%
