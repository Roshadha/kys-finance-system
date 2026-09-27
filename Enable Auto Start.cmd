@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable Auto Start.ps1"
if errorlevel 1 echo Auto-start setup failed. Read the error above.
pause
