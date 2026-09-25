@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-client-shortcut.ps1"
if errorlevel 1 echo Shortcut was not created. Check the address and try again.
pause
