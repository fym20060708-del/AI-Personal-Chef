@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
if not exist "runtime\python.exe" (
  echo Portable runtime is missing. Please extract the entire release ZIP.
  echo See README.md for developer instructions.
  pause
  exit /b 1
)
"runtime\python.exe" -I -X utf8 "scripts\launch.py"
if errorlevel 1 pause
endlocal