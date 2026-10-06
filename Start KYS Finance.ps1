param([switch]$WaitForExit)
$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'KYS Finance Server.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Server not found: $exe" }
# Serialize startup from the scheduled task, installer and desktop shortcut.
$mutex = New-Object Threading.Mutex($false, 'Local\KYSFinanceServerLaunch')
$locked = $false
try {
    try { $locked = $mutex.WaitOne(10000) } catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Another server launch is in progress.' }
    $running = @(Get-Process -Name 'KYS Finance Server' -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -ieq $exe })
    if ($running.Count -gt 0) {
        $process = $running[0]
    } else {
    $listener = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue)
    if ($listener.Count -gt 0) { throw 'Port 5000 is already used by another server. Stop that copy before starting this installation.' }
    $process = Start-Process -FilePath $exe -WorkingDirectory $PSScriptRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $PSScriptRoot 'server-startup.log') `
        -RedirectStandardError (Join-Path $PSScriptRoot 'server-error.log') -PassThru
    }
} catch {
    Add-Content -LiteralPath (Join-Path $PSScriptRoot 'launcher-error.log') -Value ((Get-Date -Format o) + ' ' + $_.Exception.Message)
    throw
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
if ($WaitForExit -and $process) {
    $process.WaitForExit()
    $process.Refresh()
    exit $process.ExitCode
}
