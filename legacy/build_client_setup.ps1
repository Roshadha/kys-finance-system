$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$client = Join-Path $root 'client'
& (Join-Path $PSScriptRoot 'build_uninstall.ps1')
& (Join-Path $root 'tmp\python38-x86\python.exe') -m PyInstaller --paths $root --noconfirm --clean --onefile --add-data "$(Join-Path $root 'build-package\uninstaller-output\KYS Finance Uninstall.exe');." --icon (Join-Path $root 'assets\kys-finance-pl.ico') --add-data "$(Join-Path $root 'assets\kys-finance-pl.ico');." --add-data "$(Join-Path $root 'assets\kys-finance-pl.png');." --windowed --name 'KYS Finance Client Setup' --distpath (Join-Path $root 'release\setup') --workpath (Join-Path $root 'build-package\client-setup') --specpath (Join-Path $root 'build-package\client-setup') --add-data "$(Join-Path $client 'KYS Client.ps1');." --add-data "$(Join-Path $client 'Install KYS Finance Client.ps1');." (Join-Path $client 'setup_gui.py')
if ($LASTEXITCODE -ne 0) { throw 'Client setup build failed.' }
