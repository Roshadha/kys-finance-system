param(
    [string]$InstallDirectory = (Join-Path $env:LOCALAPPDATA 'KYS Finance Client'),
    [string]$DesktopDirectory = [Environment]::GetFolderPath('Desktop'),
    [string]$StartupDirectory = [Environment]::GetFolderPath('Startup'),
    [switch]$SkipMonitor
)
$ErrorActionPreference = 'Stop'
$source = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'KYS Client.ps1'
New-Item -ItemType Directory -Path $installDirectory -Force | Out-Null
$launcher = Join-Path $installDirectory 'KYS Client.ps1'
if ([IO.Path]::GetFullPath($source) -ine [IO.Path]::GetFullPath($launcher)) {
    Copy-Item -LiteralPath $source -Destination $launcher -Force
}
. $launcher -FunctionsOnly
foreach ($name in @('kys-finance-pl.ico','kys-finance-pl.png')) {
    $asset = Join-Path (Split-Path -Parent $source) $name
    if ((Test-Path -LiteralPath $asset) -and [IO.Path]::GetFullPath($asset) -ine [IO.Path]::GetFullPath((Join-Path $installDirectory $name))) { Copy-Item -LiteralPath $asset -Destination $installDirectory -Force }
}
$iconSource = Join-Path (Split-Path -Parent $source) 'kys-finance-pl.ico'
if (Test-Path -LiteralPath $iconSource) {
    # A new icon path makes Explorer refresh an existing desktop shortcut's cached artwork.
    Copy-Item -LiteralPath $iconSource -Destination (Join-Path $installDirectory 'kys-finance-pl-blue-20261019.ico') -Force
}
New-KysShortcut -ShortcutDirectory $DesktopDirectory
$startup = $StartupDirectory
$link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $startup 'KYS Finance Client Discovery.lnk'))
$link.TargetPath = Join-Path $PSHOME 'powershell.exe'
$link.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $launcher + '" -Mode Monitor'
$link.WorkingDirectory = $installDirectory
$link.Save()
if (-not $SkipMonitor) { Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -WindowStyle Hidden -ArgumentList $link.Arguments }
Write-Host 'KYS Finance shortcut created on your desktop.'
Write-Host 'Connect to the company Wi-Fi/LAN and open the shortcut. It finds the server automatically.'
Write-Host 'A background check also runs at Windows sign-in and waits for the server to become available.'
Write-Host 'No Python, server EXE, or administrator access is required on this client PC.'
