@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install Company Server.ps1"
if errorlevel 1 echo Setup did not complete. Read the error above.
pause
