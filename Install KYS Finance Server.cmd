@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install KYS Finance Server.ps1"
if errorlevel 1 (
  echo.
  echo Setup did not finish. Read the error above and COMPANY_SETUP.md.
)
pause
