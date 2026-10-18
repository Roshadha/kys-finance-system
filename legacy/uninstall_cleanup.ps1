param([string]$InstallDirectory, [ValidateSet('server','client')][string]$Kind, [ValidateSet('Stop','Finalize')][string]$Phase = 'Stop')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $root 'kys-install.json'))) { throw 'Installation manifest missing.' }
$exe = Join-Path $root 'KYS Finance Server.exe'
if ($Phase -eq 'Stop') {
foreach ($process in Get-WmiObject Win32_Process) {
    if ($process.Name -ieq 'KYS Finance Server.exe' -and -not $process.ExecutablePath) {
        throw 'Cannot inspect a running Finance server. Run Uninstall as administrator and retry.'
    }
    $owned = $process.ExecutablePath -and $process.ExecutablePath -ieq $exe
    if ($Kind -eq 'client' -and $process.Name -ieq 'powershell.exe') {
        $owned = $process.CommandLine -and $process.CommandLine.Contains('"' + (Join-Path $root 'KYS Client.ps1') + '"')
    }
    if ($owned) {
        $result = $process.Terminate()
        if ($result.ReturnValue -ne 0) { throw 'Could not stop this installation. Close it and retry with the required Windows permissions.' }
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
        if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) { throw 'Server has not exited. No application files were removed. Retry after closing it.' }
    }
}
exit 0
}
$shell = New-Object -ComObject WScript.Shell
if ($Kind -eq 'server') {
    $taskService = New-Object -ComObject 'Schedule.Service'
    $taskService.Connect()
    $taskFolder = $taskService.GetFolder('\')
    $task = $null
    try { $task = $taskFolder.GetTask('KYS Finance Server') } catch { }
    if ($task) {
        $expected = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $root 'Start Company Server.ps1') + '"'
        $action = $task.Definition.Actions.Item(1)
        if ($action.Type -eq 0 -and $action.Arguments -ceq $expected) {
            $taskFolder.DeleteTask('KYS Finance Server', 0)
        }
    }
}
$sharedDesktop = if ($env:PUBLIC) { Join-Path $env:PUBLIC 'Desktop' }
$sharedStartup = if ($env:ProgramData) { Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs\Startup' }
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Startup'), $sharedDesktop, $sharedStartup) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -Unique) {
    foreach ($file in Get-ChildItem -LiteralPath $folder -Filter '*.lnk') {
        $link = $shell.CreateShortcut($file.FullName)
        if ($link.WorkingDirectory -ieq $root) { Remove-Item -LiteralPath $file.FullName }
    }
    $url = Join-Path $folder 'Open KYS Finance.url'
    if ((Test-Path -LiteralPath $url) -and ((Get-Content -LiteralPath $url) -contains ('IconFile=' + (Join-Path $root 'kys-finance-pl.ico')))) { Remove-Item -LiteralPath $url }
}
# Delete only rules associated with this exact executable. If unelevated,
# inert firewall rules may remain; never disable or broaden the firewall.
if ($Kind -eq 'server') {
    & netsh advfirewall firewall delete rule name='KYS Company HTTP' ('program=' + $exe) | Out-Null
    & netsh advfirewall firewall delete rule name='KYS Company Discovery' ('program=' + $exe) | Out-Null
}
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\KYSFinance' + (Get-Culture).TextInfo.ToTitleCase($Kind)
if (Test-Path -LiteralPath $key) {
    if ((Get-ItemProperty -LiteralPath $key).InstallLocation -ieq $root) { Remove-Item -LiteralPath $key }
}
