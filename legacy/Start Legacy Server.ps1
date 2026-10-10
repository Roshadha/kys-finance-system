# Compatible with Windows PowerShell 2.0 (Windows 7 SP1).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'KYS Finance Server.exe'
$mutex = New-Object Threading.Mutex($false, 'Local\KYSFinanceLegacyLaunch')
$locked = $false
try {
    try { $locked = $mutex.WaitOne(10000) } catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Another launch is in progress.' }
    if (-not (Test-Path -LiteralPath $exe)) { throw 'Extract the entire ZIP first.' }
    $existing = @(Get-Process -Name 'KYS Finance Server' -ErrorAction SilentlyContinue | Where-Object { $_.Path -ieq $exe })
    if ($existing.Count -eq 0) {
        $listeners = @([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object { $_.Port -eq 5000 })
        if ($listeners.Count) { throw 'Port 5000 is used by another app/server. Do not run two copies.' }
        $env:KYS_HOST = '127.0.0.1'
        $env:PORT = '5000'
        # PowerShell 2.0 cannot combine WindowStyle with output redirection.
        # Start independently without a console; the Python entry point logs.
        $info = New-Object Diagnostics.ProcessStartInfo
        $info.FileName = $exe
        $info.WorkingDirectory = $root
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        [Diagnostics.Process]::Start($info) | Out-Null
    }
} catch {
    Add-Content -LiteralPath (Join-Path $root 'launcher-error.log') -Value ((Get-Date -Format o) + ' ' + $_.Exception.Message)
    throw
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Close()
}
