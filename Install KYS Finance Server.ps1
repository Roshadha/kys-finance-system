param(
    [string]$InstallDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'KYS Finance Server'),
    [string]$ShortcutDirectory = [Environment]::GetFolderPath('Desktop')
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
if ($sourcePath -ine $installPath) {
    if (Test-Path -LiteralPath $installPath) {
        throw "Installation folder already exists: $installPath. To protect existing data, this setup will not overwrite it. Read COMPANY_SETUP.md for update steps."
    }
    if (Test-Path -LiteralPath (Join-Path $sourcePath 'data\kys_finance.db')) {
        throw 'This source folder contains a live database. Follow the migration steps in COMPANY_SETUP.md instead of creating a second copy.'
    }
    New-Item -ItemType Directory -Path $installPath -ErrorAction Stop | Out-Null
    foreach ($name in @('KYS Finance Server.exe', '_internal', 'COMPANY_SETUP.md',
            'create-client-shortcut.ps1', 'Create Client Shortcut.cmd',
            'Open KYS Finance on Server.url', 'Install KYS Finance Server.ps1',
            'Install KYS Finance Server.cmd')) {
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
$serverShortcut.TargetPath = Join-Path $installPath 'KYS Finance Server.exe'
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
Write-Host 'Start the server shortcut first. Keep its window open, then open the browser shortcut.'
