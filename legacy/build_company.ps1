$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$destination = Join-Path $root 'release\company-win7'
if (Test-Path -LiteralPath (Join-Path $destination 'KYS Finance Server\data')) { throw 'Data exists in build output; refusing overwrite.' }
& (Join-Path $root 'tmp\python38-x86\python.exe') -m PyInstaller --paths $root --noconfirm --clean --onedir --icon (Join-Path $root 'assets\kys-finance-pl.ico') --console --name 'KYS Finance Server' --exclude-module pandas --exclude-module numpy --paths $root --distpath $destination --workpath (Join-Path $root 'build-package\company') --specpath (Join-Path $root 'build-package\company') --add-data "$(Join-Path $root 'templates');templates" --add-data "$(Join-Path $root 'static');static" (Join-Path $PSScriptRoot 'server_company.py')
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$output = Join-Path $destination 'KYS Finance Server'
foreach ($name in @('Install Company Server.cmd','Install Company Server.ps1','Create Company Shortcuts.ps1','Configure Company Auto Start.ps1','Start Company Server.ps1','Stop Company Server.ps1','Enable Company Network.ps1','Restore KYS Backup.cmd','Restore Server Control.ps1','COMPANY-INSTALL.md','COMPANY-VERIFICATION.md','BACKUP-GUIDE.md')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $output -Force
}
foreach ($name in @('Configure External Backup.cmd','Configure External Backup.ps1','client')) {
    Copy-Item -LiteralPath (Join-Path $root $name) -Destination $output -Recurse -Force
}
