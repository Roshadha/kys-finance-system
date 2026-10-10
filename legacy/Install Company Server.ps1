$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'KYS Finance Server.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Extract the entire package first.' }
if ((Test-Path -LiteralPath (Join-Path $root 'data\kys_finance.db')) -and -not (Test-Path -LiteralPath (Join-Path $root 'company-installation.txt'))) { throw 'An unrecognized database exists here. Do not overwrite or migrate live data with this installer. Use a clean folder.' }
$shell = New-Object -ComObject WScript.Shell
$arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $root 'Start Company Server.ps1') + '"'
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Startup'))) {
    $path = Join-Path $folder 'KYS Finance Server.lnk'
    if ((Test-Path -LiteralPath $path) -and $shell.CreateShortcut($path).Arguments -cne $arguments) { throw 'A shortcut points to another installation. Stop and inspect it before continuing.' }
}
Set-Content -LiteralPath (Join-Path $root 'company-installation.txt') -Value 'Company package; configure in place; preserve data.'
& $exe --configure-admin
if ($LASTEXITCODE -ne 0) { throw 'Administrator configuration or runtime check failed. On Windows 7 install the prerequisites in COMPANY-INSTALL.md and restart.' }
& (Join-Path $root 'Enable Company Network.ps1')
Set-Content -LiteralPath (Join-Path $root 'setup-complete.txt') -Value 'Configured'
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Startup'))) {
    $link = $shell.CreateShortcut((Join-Path $folder 'KYS Finance Server.lnk'))
    $link.TargetPath = Join-Path $PSHOME 'powershell.exe'
    $link.Arguments = $arguments
    $link.WorkingDirectory = $root
    $link.WindowStyle = 7
    $link.Save()
}
Set-Content -LiteralPath (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Open KYS Finance.url') -Encoding ASCII -Value @('[InternetShortcut]','URL=http://127.0.0.1:5000/')
& (Join-Path $root 'Start Company Server.ps1')
$ready = $false
for ($i=0; $i -lt 30; $i++) {
    try {
        $request = [Net.WebRequest]::Create('http://127.0.0.1:5000/health')
        $request.Timeout = 2000
        $response = $request.GetResponse(); $response.Close(); $ready = $true; break
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) { throw 'Startup health check failed. Check server-error.log.' }
Write-Host 'Setup complete. Keep this folder permanently. Server starts after this Windows user signs in.'
Write-Host 'Select Home/Work (Private) for the trusted company network. Configure an external backup before handover.'
Start-Process 'http://127.0.0.1:5000/'
