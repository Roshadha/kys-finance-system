$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'KYS Finance Server.exe'
$mutex = New-Object Threading.Mutex($false, 'Local\KYSFinanceCompanyLaunch')
$locked = $false
try {
    $locked = $mutex.WaitOne(10000)
    if (-not $locked) { throw 'Another launch is in progress.' }
    if (-not (Test-Path -LiteralPath (Join-Path $root 'setup-complete.txt'))) { throw 'Run Install Company Server.cmd first.' }
    $existing = @(Get-Process -Name 'KYS Finance Server' -ErrorAction SilentlyContinue | Where-Object { $_.Path -ieq $exe })
    if ($existing.Count) { return }
    if (@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object { $_.Port -eq 5000 }).Count) { throw 'Port 5000 is occupied. Stop the other server before starting this installation.' }
    $env:KYS_HOST = '0.0.0.0'
    $env:PORT = '5000'
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $exe
    $info.WorkingDirectory = $root
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    [Diagnostics.Process]::Start($info) | Out-Null
} catch {
    Add-Content -LiteralPath (Join-Path $root 'launcher-error.log') -Value ((Get-Date -Format o) + ' ' + $_.Exception.Message)
    throw
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Close()
}
