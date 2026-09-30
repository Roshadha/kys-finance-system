$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$existingDatabase = Join-Path $projectRoot 'release\KYS Finance Server\data\kys_finance.db'
if (Test-Path -LiteralPath $existingDatabase) {
  throw 'A live database exists in the release folder. Move the installed server elsewhere and back up its data before rebuilding.'
}
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Run setup.bat first to create the Python environment.' }
& $pythonExe -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Install the packaging dependency: .venv\Scripts\python.exe -m pip install pyinstaller' }
& $pythonExe -m PyInstaller --noconfirm --clean --onedir --console --name 'KYS Finance Server' `
  --distpath (Join-Path $projectRoot 'release') `
  --workpath (Join-Path $projectRoot 'build-package') `
  --specpath (Join-Path $projectRoot 'build-package') `
  --add-data "$(Join-Path $projectRoot 'templates');templates" `
  --add-data "$(Join-Path $projectRoot 'static');static" `
  (Join-Path $projectRoot 'server.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
foreach ($name in @('COMPANY_SETUP.md', 'create-client-shortcut.ps1', 'Create Client Shortcut.cmd',
        'Install KYS Finance Server.ps1', 'Install KYS Finance Server.cmd',
        'Enable Auto Start.ps1', 'Enable Auto Start.cmd',
        'Configure External Backup.ps1', 'Configure External Backup.cmd',
        'Open KYS Finance on Server.url', 'Enable Network Access.ps1', 'Enable Network Access.cmd')) {
  Copy-Item -LiteralPath (Join-Path $projectRoot $name) `
    -Destination (Join-Path $projectRoot 'release\KYS Finance Server') -Force
}
$clientDestination = Join-Path $projectRoot 'release\KYS Finance Server\client'
New-Item -ItemType Directory -Path $clientDestination -Force | Out-Null
foreach ($name in @('KYS Client.ps1', 'Install KYS Finance Client.ps1', 'Install KYS Finance Client.cmd', 'README.txt')) {
    Copy-Item -LiteralPath (Join-Path $projectRoot "client\$name") -Destination $clientDestination -Force
}
Write-Host "Ready: $(Join-Path $projectRoot 'release\KYS Finance Server\KYS Finance Server.exe')"
