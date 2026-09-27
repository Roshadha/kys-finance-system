param(
    [string]$Destination,
    [string]$InstallDirectory = (Split-Path -Parent $MyInvocation.MyCommand.Path)
)

$ErrorActionPreference = 'Stop'
$installPath = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $installPath 'KYS Finance Server.exe') -PathType Leaf)) {
    throw 'Run this helper from the installed KYS Finance Server folder.'
}
if (-not $Destination) {
    $Destination = Read-Host 'External USB/NAS backup folder (example E:\KYS-Backups or \\NAS\FinanceBackups)'
}
if (-not $Destination -or -not [IO.Path]::IsPathRooted($Destination)) {
    throw 'Enter a full path to an existing external drive or NAS folder.'
}
$target = [IO.Path]::GetFullPath($Destination)
if ($target -ne [IO.Path]::GetPathRoot($target)) { $target = $target.TrimEnd('\') }
if (-not (Test-Path -LiteralPath $target -PathType Container)) {
    throw "Backup folder is not available: $target"
}
if ($target -ieq $installPath -or $target.StartsWith($installPath + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The backup folder must be outside the application folder.'
}
if ([IO.Path]::GetPathRoot($target) -ieq [IO.Path]::GetPathRoot($installPath)) {
    throw 'Choose another drive or NAS share; a folder on the server disk is not disaster protection.'
}
Set-Content -LiteralPath (Join-Path $installPath 'backup-target.txt') -Value $target -Encoding UTF8
Write-Host "External backup location set to: $target"
Write-Host 'The next server backup will copy a verified daily snapshot there. Keep this drive/share available.'
