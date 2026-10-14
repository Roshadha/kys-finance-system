param([ValidateSet('Stop','Restart')][string]$Mode, [int]$WizardPid)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'KYS Finance Server.exe'
if ($Mode -eq 'Restart') {
    Wait-Process -Id $WizardPid -ErrorAction SilentlyContinue
    & (Join-Path $root 'Start Company Server.ps1')
    exit
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'restore.lock'))) { throw 'Restore lock missing.' }
$mutex = New-Object Threading.Mutex($false, 'Local\KYSFinanceCompanyLaunch')
$locked = $false
try {
    $locked = $mutex.WaitOne(10000)
    if (-not $locked) { throw 'Server launch in progress.' }
    $processes = @(Get-WmiObject Win32_Process -Filter "Name='KYS Finance Server.exe'" | Where-Object { $_.ExecutablePath -ieq $exe -and $_.ProcessId -ne $WizardPid })
    foreach ($process in $processes) {
        if ($process.CommandLine -like '*--restore*') { throw 'Another restore window is open. Close it first.' }
        if ($process.Terminate().ReturnValue -ne 0) { throw 'Unable to stop server.' }
        Wait-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
    }
    if (@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object { $_.Port -eq 5000 }).Count) {
        throw 'A server is still listening on port 5000. Restore cannot continue.'
    }
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Close()
}
