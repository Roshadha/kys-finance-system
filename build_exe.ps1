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
Write-Host "Ready: $(Join-Path $projectRoot 'release\KYS Finance Server\KYS Finance Server.exe')"
