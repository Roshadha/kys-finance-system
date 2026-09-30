@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable Network Access.ps1"
if errorlevel 1 echo Network setup failed. Run from the installed server folder with administrator permission.
pause
