@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install Legacy Test.ps1"
if errorlevel 1 echo Setup failed. Read the message above.
pause
