@echo off
rem AGENT: Shim — HUD DLL build moved under cpp/src/native/hud_dcomp/
cd /d "%~dp0..\..\cpp\src\native\hud_dcomp"
call build.bat %*
