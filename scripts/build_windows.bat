@echo off
setlocal
cd /d "%~dp0.."

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "scripts\build_windows.py"
) else (
    py -3 "scripts\build_windows.py"
)

if errorlevel 1 exit /b %errorlevel%
endlocal
