param(
    [string]$ServerAddress,
    [int]$Port = 5000,
    [string]$ShortcutDirectory = [Environment]::GetFolderPath('Desktop')
)

if (-not $ServerAddress) {
    $ServerAddress = Read-Host "Enter the server PC's LAN IP address (example 192.168.1.50)"
}
if ($ServerAddress -notmatch '^[A-Za-z0-9.-]+$') {
    throw 'Enter a LAN IP address or computer name only, without http:// or a port.'
}
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be between 1 and 65535.' }
if (-not (Test-Path -LiteralPath $ShortcutDirectory -PathType Container)) {
    throw "Desktop folder does not exist: $ShortcutDirectory"
}
$shortcut = Join-Path $ShortcutDirectory 'KYS Finance.url'
$url = "http://${ServerAddress}:${Port}/"
Set-Content -LiteralPath $shortcut -Encoding ASCII -Value @(
    '[InternetShortcut]'
    "URL=$url"
)
Write-Host "Desktop shortcut created: $shortcut"
Write-Host "Opens: $url"
