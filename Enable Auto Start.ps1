param([string]$InstallDirectory = (Split-Path -Parent $MyInvocation.MyCommand.Path))

$ErrorActionPreference = 'Stop'
$installPath = [IO.Path]::GetFullPath($InstallDirectory)
$exe = Join-Path $installPath 'KYS Finance Server.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Server EXE not found: $exe" }

$taskName = 'KYS Finance Server Auto Start'
$userName = [Security.Principal.WindowsIdentity]::GetCurrent().Name
try {
    Import-Module ScheduledTasks -ErrorAction Stop
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    $launcher = Join-Path $installPath 'Start KYS Finance.ps1'
    $powershell = Join-Path $PSHOME 'powershell.exe'
    $launchArguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $launcher + '" -WaitForExit'
    if ($existing -and -not (($existing.Actions.Execute -ieq $exe) -or
            ($existing.Actions.Execute -ieq $powershell -and $existing.Actions.Arguments -ceq $launchArguments))) {
        throw "A different task already uses the name $taskName. Ask IT to inspect Task Scheduler."
    }
    $action = New-ScheduledTaskAction -Execute $powershell -Argument $launchArguments -WorkingDirectory $installPath
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $userName
    $principal = New-ScheduledTaskPrincipal -UserId $userName -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew `
        -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Principal $principal -Settings $settings -Description 'Start KYS Finance when this Windows user signs in' `
        -Force -ErrorAction Stop | Out-Null
    Write-Host "Auto-start enabled for $userName via Windows Task Scheduler."
    Write-Host 'It starts when this user signs in after a reboot, not before Windows sign-in.'
} catch {
    if ($_.Exception.Message -like 'A different task already uses*') { throw }
    $startup = [Environment]::GetFolderPath('Startup')
    if (-not (Test-Path -LiteralPath $startup -PathType Container)) { throw }
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $startup 'KYS Finance Server.lnk'))
    $shortcut.TargetPath = Join-Path $PSHOME 'powershell.exe'
    $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $installPath 'Start KYS Finance.ps1') + '"'
    $shortcut.WindowStyle = 7
    $shortcut.WorkingDirectory = $installPath
    $shortcut.Save()
    Write-Warning "Task Scheduler was unavailable ($($_.Exception.Message)). A Windows Startup shortcut was created instead."
    Write-Host 'It starts when this user signs in after a reboot; it does not automatically restart after a crash.'
}
