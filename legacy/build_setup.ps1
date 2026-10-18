param([switch]$SetupOnly)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not $SetupOnly) {
& (Join-Path $PSScriptRoot 'build_uninstall.ps1')
& (Join-Path $PSScriptRoot 'build_company.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Server build failed.' }
$server = Join-Path $root 'release\company-win7\KYS Finance Server'
Copy-Item -LiteralPath (Join-Path $root 'build-package\uninstaller-output\KYS Finance Uninstall.exe') -Destination $server -Force
foreach ($name in @('kys-finance-pl.ico','kys-finance-pl.png')) { Copy-Item -LiteralPath (Join-Path $root ('assets\' + $name)) -Destination $server -Force }
$unsafe = Get-ChildItem -LiteralPath $server -Recurse -Force | Where-Object { $_.Name -match '\.db($|-)|^\.secret_key$|^backup-target\.txt$|^setup-complete\.txt$|^company-installation\.txt$' -or ($_.PSIsContainer -and $_.Name -in @('data','backups','restore-recovery')) }
if ($unsafe) { throw 'Runtime data in package. Refusing to build installer.' }
$payload = Join-Path $root 'build-package\server-payload.zip'
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path -LiteralPath $payload) { Remove-Item -LiteralPath $payload }
[IO.Compression.ZipFile]::CreateFromDirectory($server, $payload)
} else {
    $payload = Join-Path $root 'build-package\server-payload.zip'
    if (-not (Test-Path -LiteralPath $payload)) { throw 'Server payload is missing. Run the full setup build first.' }
}
& (Join-Path $root 'tmp\python38-x86\python.exe') -m PyInstaller --paths $root --noconfirm --clean --onefile --icon (Join-Path $root 'assets\kys-finance-pl.ico') --add-data "$(Join-Path $root 'assets\kys-finance-pl.ico');." --add-data "$(Join-Path $root 'assets\kys-finance-pl.png');." --add-data "$(Join-Path $PSScriptRoot 'Create Company Shortcuts.ps1');." --windowed --uac-admin --name 'KYS Finance Setup' --distpath (Join-Path $root 'release\setup') --workpath (Join-Path $root 'build-package\setup') --specpath (Join-Path $root 'build-package\setup') --add-data "$payload;." (Join-Path $PSScriptRoot 'setup_gui.py')
if ($LASTEXITCODE -ne 0) { throw 'Setup build failed.' }
