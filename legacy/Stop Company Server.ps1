param([switch]$NoConfirm)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'KYS Finance Server.exe'
$log = Join-Path $root 'server-stop.log'
Add-Type -AssemblyName System.Windows.Forms
function Show-StopDialog([string]$Text, [string]$Title, $Buttons, $Icon) {
    $owner = New-Object Windows.Forms.Form
    $owner.TopMost = $true
    $owner.ShowInTaskbar = $false
    $owner.Opacity = 0
    $owner.StartPosition = [Windows.Forms.FormStartPosition]::CenterScreen
    try {
        $owner.Show()
        return [Windows.Forms.MessageBox]::Show($owner, $Text, $Title, $Buttons, $Icon)
    } finally { $owner.Close(); $owner.Dispose() }
}

if (Test-Path -LiteralPath (Join-Path $root 'restore.lock')) {
    Show-StopDialog 'A database restore is in progress. Wait for it to finish.' 'K.Y.S. Finance' ([Windows.Forms.MessageBoxButtons]::OK) ([Windows.Forms.MessageBoxIcon]::Warning) | Out-Null
    exit 1
}

if (-not $NoConfirm) {
    $answer = Show-StopDialog 'Stop the K.Y.S. Finance server? Ask all users to finish saving first. A verified LOCAL backup will be taken; other computers will lose access until you start it again.' 'Stop K.Y.S. Finance' ([Windows.Forms.MessageBoxButtons]::YesNo) ([Windows.Forms.MessageBoxIcon]::Question)
    if ($answer -ne [Windows.Forms.DialogResult]::Yes) { exit 0 }
}

$mutex = New-Object Threading.Mutex($false, 'Local\KYSFinanceCompanyLaunch')
$locked = $false
try {
    $locked = $mutex.WaitOne(10000)
    if (-not $locked) { throw 'Server launch is busy. Try again.' }
    $processes = @(Get-WmiObject Win32_Process -Filter "Name='KYS Finance Server.exe'" |
        Where-Object { $_.ExecutablePath -ieq $exe })
    foreach ($process in $processes) {
        if ($process.CommandLine -like '*--restore*') { throw 'A restore window is open. Finish it first.' }
    }
    if (-not $processes.Count) {
        if (@([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object { $_.Port -eq 5000 }).Count) {
            throw 'A server is listening on port 5000, but it is not the installation linked to this shortcut. Use the Stop shortcut from the running server folder.'
        }
        if (-not $NoConfirm) { Show-StopDialog 'The K.Y.S. Finance server is already stopped.' 'K.Y.S. Finance' ([Windows.Forms.MessageBoxButtons]::OK) ([Windows.Forms.MessageBoxIcon]::Information) | Out-Null }
        exit 0
    }
    $resultPath = Join-Path $root 'shutdown-result.json'
    if (Test-Path -LiteralPath $resultPath) { Remove-Item -LiteralPath $resultPath }
    [IO.File]::WriteAllText((Join-Path $root 'shutdown.request'), [Guid]::NewGuid().ToString('N'))
    Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' Requested graceful drain and local backup.')
    $deadline = (Get-Date).AddSeconds(120)
    foreach ($process in $processes) {
        while ((Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) {
            if ((Test-Path -LiteralPath $resultPath) -and ([IO.File]::ReadAllText($resultPath) -match '"status"\s*:\s*"failed"')) {
                throw ('Stop cancelled: ' + [IO.File]::ReadAllText($resultPath))
            }
            Start-Sleep -Milliseconds 250
        }
        if (Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue) { throw 'Server did not finish graceful shutdown. Check server-error.log. No process was force-killed.' }
    }
    Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' Server stopped.')
    if (-not $NoConfirm) { Show-StopDialog 'Server stopped. Use the KYS Finance Server shortcut to start it again.' 'K.Y.S. Finance' ([Windows.Forms.MessageBoxButtons]::OK) ([Windows.Forms.MessageBoxIcon]::Information) | Out-Null }
} catch {
    Add-Content -LiteralPath $log -Value ((Get-Date -Format o) + ' Stop failed: ' + $_.Exception.Message)
    if ($NoConfirm) { Write-Error $_.Exception.Message } else { Show-StopDialog $_.Exception.Message 'K.Y.S. Finance' ([Windows.Forms.MessageBoxButtons]::OK) ([Windows.Forms.MessageBoxIcon]::Error) | Out-Null }
    exit 1
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Close()
}
