$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root 'tmp\python38-x86\python.exe') -m PyInstaller --paths $root --noconfirm --clean --onefile --windowed --name 'KYS Finance Uninstall' --icon (Join-Path $root 'assets\kys-finance-pl.ico') --distpath (Join-Path $root 'build-package\uninstaller-output') --workpath (Join-Path $root 'build-package\uninstaller') --specpath (Join-Path $root 'build-package\uninstaller') --add-data "$(Join-Path $root 'assets\kys-finance-pl.ico');." --add-data "$(Join-Path $root 'assets\kys-finance-pl.png');." --add-data "$(Join-Path $PSScriptRoot 'uninstall_cleanup.ps1');." (Join-Path $PSScriptRoot 'uninstall_gui.py')
if ($LASTEXITCODE -ne 0) { throw 'Uninstaller build failed.' }
