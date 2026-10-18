param([Parameter(Mandatory=$true)][string]$InstallDirectory)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
$exe = Join-Path $root 'KYS Finance Server.exe'
if (-not (Test-Path -LiteralPath $exe) -or -not (Test-Path -LiteralPath (Join-Path $root 'setup-complete.txt'))) {
    throw 'Choose a completed KYS Finance server installation.'
}
# Windows 7's .NET SpecialFolder enum does not expose CommonDesktopDirectory
# or CommonStartup. These environment-backed locations exist on Windows 7–11.
if (-not $env:PUBLIC -or -not $env:ProgramData) { throw 'Windows shared folder paths are unavailable.' }
$desktop = Join-Path $env:PUBLIC 'Desktop'
$startup = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\Startup'
if (-not (Test-Path -LiteralPath $desktop -PathType Container) -or
    -not (Test-Path -LiteralPath $startup -PathType Container)) {
    throw 'Windows shared Desktop or Startup folder is unavailable.'
}
$shell = New-Object -ComObject WScript.Shell
$icon = Join-Path $root 'kys-finance-pl.ico'
$restorePath = Join-Path $desktop 'Restore KYS Backup.lnk'
if (Test-Path -LiteralPath $restorePath) {
    $existing = $shell.CreateShortcut($restorePath)
    if ($existing.TargetPath -ine $exe -or $existing.WorkingDirectory -ine $root) { throw 'Restore shortcut belongs to another installation.' }
}
$stopPath = Join-Path $desktop 'Stop KYS Finance Server.lnk'
$stopScript = Join-Path $root 'Stop Company Server.ps1'
if (Test-Path -LiteralPath $stopPath) {
    $existing = $shell.CreateShortcut($stopPath)
    if ($existing.WorkingDirectory -ine $root -or $existing.Arguments -notlike ('*' + $stopScript + '*')) { throw 'Stop shortcut belongs to another installation.' }
}
$startScript = Join-Path $root 'Start Company Server.ps1'
$arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $startScript + '"'
foreach ($folder in @($desktop, $startup)) {
    $path = Join-Path $folder 'KYS Finance Server.lnk'
    if (Test-Path -LiteralPath $path) {
        $existing = $shell.CreateShortcut($path)
        if ($existing.WorkingDirectory -ine $root -or $existing.Arguments -cne $arguments) { throw 'Server shortcut belongs to another installation.' }
    }
}
$openPath = Join-Path $desktop 'Open KYS Finance.url'
if ((Test-Path -LiteralPath $openPath) -and -not ((Get-Content -LiteralPath $openPath) -contains ('IconFile=' + $icon))) {
    throw 'Open shortcut belongs to another installation.'
}
$restoreLink = $shell.CreateShortcut($restorePath)
$restoreLink.TargetPath = $exe
$restoreLink.Arguments = '--restore'
$restoreLink.WorkingDirectory = $root
$restoreLink.IconLocation = $icon
$restoreLink.Save()
$stopLink = $shell.CreateShortcut($stopPath)
$stopLink.TargetPath = Join-Path $PSHOME 'powershell.exe'
$stopLink.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $stopScript + '"'
$stopLink.WorkingDirectory = $root
$stopLink.WindowStyle = 7
$stopLink.IconLocation = $icon
$stopLink.Save()
foreach ($folder in @($desktop, $startup)) {
    $link = $shell.CreateShortcut((Join-Path $folder 'KYS Finance Server.lnk'))
    $link.TargetPath = Join-Path $PSHOME 'powershell.exe'
    $link.Arguments = $arguments
    $link.WorkingDirectory = $root
    $link.WindowStyle = 7
    $link.IconLocation = $icon
    $link.Save()
}
Set-Content -LiteralPath $openPath -Encoding ASCII -Value @('[InternetShortcut]','URL=http://127.0.0.1:5000/', ('IconFile=' + $icon), 'IconIndex=0')
Write-Host 'Shared Desktop and sign-in Startup shortcuts are ready.'
