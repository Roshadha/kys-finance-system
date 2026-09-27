@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Configure External Backup.ps1"
if errorlevel 1 echo Backup location was not changed. Read the error above.
pause
