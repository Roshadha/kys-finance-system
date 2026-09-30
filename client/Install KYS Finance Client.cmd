@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install KYS Finance Client.ps1"
if errorlevel 1 echo Client setup failed. Please read the message above.
pause
