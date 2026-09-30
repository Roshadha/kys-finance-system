$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'KYS Client.ps1'
$installDirectory = Join-Path $env:LOCALAPPDATA 'KYS Finance Client'
New-Item -ItemType Directory -Path $installDirectory -Force | Out-Null
$launcher = Join-Path $installDirectory 'KYS Client.ps1'
if ([IO.Path]::GetFullPath($source) -ine [IO.Path]::GetFullPath($launcher)) {
    Copy-Item -LiteralPath $source -Destination $launcher -Force
}
. $launcher -FunctionsOnly
New-KysShortcut
$startup = [Environment]::GetFolderPath('Startup')
$link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $startup 'KYS Finance Client Discovery.lnk'))
$link.TargetPath = Join-Path $PSHOME 'powershell.exe'
$link.Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $launcher + '" -Mode Monitor'
$link.WorkingDirectory = $installDirectory
$link.Save()
Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -WindowStyle Hidden -ArgumentList $link.Arguments
Write-Host 'KYS Finance shortcut created on your desktop.'
Write-Host 'Connect to the company Wi-Fi/LAN and open the shortcut. It finds the server automatically.'
Write-Host 'A background check also runs at Windows sign-in and waits for the server to become available.'
Write-Host 'No Python, server EXE, or administrator access is required on this client PC.'
