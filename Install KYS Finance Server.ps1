param(
    [string]$InstallDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'KYS Finance Server'),
    [string]$ShortcutDirectory = [Environment]::GetFolderPath('Desktop'),
    [switch]$SkipStartupRegistration,
    [switch]$SkipLaunch
)

$ErrorActionPreference = 'Stop'
$sourceDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceExecutable = Join-Path $sourceDirectory 'KYS Finance Server.exe'
$sourceInternal = Join-Path $sourceDirectory '_internal'
if (-not (Test-Path -LiteralPath $sourceExecutable -PathType Leaf) -or
    -not (Test-Path -LiteralPath $sourceInternal -PathType Container)) {
    throw 'Extract the full release ZIP first, then run this installer from inside the KYS Finance Server folder.'
}

$sourcePath = [IO.Path]::GetFullPath($sourceDirectory).TrimEnd('\')
$installPath = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
# An existing database must keep one authoritative home. Configure that copy
# in place rather than creating a second writable company database.
if (Test-Path -LiteralPath (Join-Path $sourcePath 'data\kys_finance.db')) {
    $installPath = $sourcePath
    Write-Host "Existing company data found. Configuring this folder in place: $installPath"
    Write-Host 'Keep this folder permanently; do not delete or move it after setup.'
}
if ($sourcePath -ine $installPath) {
    if (Test-Path -LiteralPath $installPath) {
        throw "Installation folder already exists: $installPath. To protect existing data, this setup will not overwrite it. Read COMPANY_SETUP.md for update steps."
    }
    New-Item -ItemType Directory -Path $installPath -ErrorAction Stop | Out-Null
    foreach ($name in @('KYS Finance Server.exe', '_internal', 'COMPANY_SETUP.md',
            'create-client-shortcut.ps1', 'Create Client Shortcut.cmd',
            'Open KYS Finance on Server.url', 'Install KYS Finance Server.ps1',
            'Install KYS Finance Server.cmd', 'Enable Auto Start.ps1',
            'Enable Auto Start.cmd', 'Configure External Backup.ps1',
            'Configure External Backup.cmd', 'Enable Network Access.ps1',
            'Enable Network Access.cmd', 'Start KYS Finance.ps1', 'client')) {
        $item = Join-Path $sourcePath $name
        if (Test-Path -LiteralPath $item) {
            Copy-Item -LiteralPath $item -Destination $installPath -Recurse -ErrorAction Stop
        }
    }
}

if (-not (Test-Path -LiteralPath $ShortcutDirectory -PathType Container)) {
    throw "Desktop folder does not exist: $ShortcutDirectory"
}
$shell = New-Object -ComObject WScript.Shell
$serverShortcut = $shell.CreateShortcut((Join-Path $ShortcutDirectory 'Start KYS Finance Server.lnk'))
$serverShortcut.TargetPath = Join-Path $PSHOME 'powershell.exe'
$serverShortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $installPath 'Start KYS Finance.ps1') + '"'
$serverShortcut.WindowStyle = 7
$serverShortcut.WorkingDirectory = $installPath
$serverShortcut.IconLocation = Join-Path $installPath 'KYS Finance Server.exe'
$serverShortcut.Description = 'Start the KYS Finance server on this PC'
$serverShortcut.Save()

Set-Content -LiteralPath (Join-Path $ShortcutDirectory 'Open KYS Finance.url') -Encoding ASCII -Value @(
    '[InternetShortcut]'
    'URL=http://127.0.0.1:5000/'
)
Write-Host "Installed in: $installPath"
Write-Host 'Desktop shortcuts created: Start KYS Finance Server, Open KYS Finance'
if (-not $SkipStartupRegistration) {
    & (Join-Path $installPath 'Enable Auto Start.ps1') -InstallDirectory $installPath
}
& (Join-Path $installPath 'Enable Network Access.ps1')
if (-not $SkipLaunch) {
    $startupTask = Get-ScheduledTask -TaskName 'KYS Finance Server Auto Start' -ErrorAction SilentlyContinue
    if (-not $SkipStartupRegistration -and $startupTask) {
        Start-ScheduledTask -TaskName 'KYS Finance Server Auto Start'
    } else {
        & (Join-Path $installPath 'Start KYS Finance.ps1')
    }
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:5000/health' -TimeoutSec 2
            if ($health.service -eq 'kys-finance' -and $health.status -eq 'ok') { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Settings saved, but server health check failed. Check server-startup.log in the installed folder.' }
    Start-Process 'http://127.0.0.1:5000/'
}
Write-Host 'Setup complete: shortcuts, automatic sign-in startup and Private LAN firewall rules are enabled.'
Write-Host 'After restarting Windows, sign in with this same Windows account. No manual server launch is needed.'
Write-Host 'For a trusted company network, select Private in Windows network settings. Public networks remain blocked.'
Write-Host 'Local backups run automatically. Configure External Backup.cmd still needs your external drive or NAS destination.'
Write-Host 'Copy the client folder to each staff PC and run Install KYS Finance Client.cmd there.'
