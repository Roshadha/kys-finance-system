$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root 'tmp\python38-x86\python.exe'
$destination = Join-Path $root 'release\win7-test'
if (Test-Path -LiteralPath (Join-Path $destination 'KYS Finance Server\data')) { throw 'Test data found in output; refusing to overwrite it.' }
& $python -m PyInstaller --noconfirm --clean --onedir --console --name 'KYS Finance Server' --exclude-module pandas --exclude-module numpy --paths $root --distpath $destination --workpath (Join-Path $root 'build-package\win7') --specpath (Join-Path $root 'build-package\win7') --add-data "$(Join-Path $root 'templates');templates" --add-data "$(Join-Path $root 'static');static" (Join-Path $PSScriptRoot 'server_win7.py')
if ($LASTEXITCODE -ne 0) { throw 'Legacy build failed' }
foreach ($name in @('Install Legacy Test.ps1','Install Legacy Test.cmd','Start Legacy Server.ps1','Check Legacy Server.ps1','Check Legacy Server.cmd','README-WIN7-TEST.md','TEST-RESULTS.md')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $destination 'KYS Finance Server') -Force
}
