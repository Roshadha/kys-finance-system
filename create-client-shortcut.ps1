param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9.-]+$')]
    [string]$ServerAddress,
    [int]$Port = 5000
)

if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be between 1 and 65535.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = Join-Path $desktop 'KYS Finance.url'
$url = "http://${ServerAddress}:${Port}/"
Set-Content -LiteralPath $shortcut -Encoding ASCII -Value @(
    '[InternetShortcut]'
    "URL=$url"
)
Write-Host "Desktop shortcut created: $shortcut"
Write-Host "Opens: $url"
