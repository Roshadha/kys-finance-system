# In-place test setup only. Does not touch another installation or database.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path -LiteralPath (Join-Path $root 'KYS Finance Server.exe'))) { throw 'Extract the complete ZIP first.' }
if (Test-Path -LiteralPath (Join-Path $root 'data\kys_finance.db')) {
    throw 'This is an isolated TEST setup. A database already exists here; use the existing Start shortcut. Do not overwrite company data.'
}
$shell = New-Object -ComObject WScript.Shell
$launcher = Join-Path $root 'Start Legacy Server.ps1'
$arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $launcher + '"'
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Startup'))) {
    $path = Join-Path $folder 'KYS Finance Legacy TEST.lnk'
    $shortcut = $shell.CreateShortcut($path)
    if ((Test-Path -LiteralPath $path) -and $shortcut.Arguments -cne $arguments) { throw 'A legacy shortcut points to another installation. Inspect it first.' }
    $shortcut.TargetPath = Join-Path $PSHOME 'powershell.exe'
    $shortcut.Arguments = $arguments
    $shortcut.WorkingDirectory = $root
    $shortcut.WindowStyle = 7
    $shortcut.Save()
}
$url = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Open KYS Legacy TEST.url'
Set-Content -LiteralPath $url -Encoding ASCII -Value @('[InternetShortcut]', 'URL=http://127.0.0.1:5000/')
& $launcher
Write-Host 'Test shortcuts created. Startup runs AFTER this Windows user signs in.'
Write-Host 'Run Check Legacy Server.cmd next. Keep this extracted folder in place.'
Write-Host 'Local test only: no firewall changes, no LAN access, no live-data migration.'
