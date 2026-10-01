# Non-mutating launcher checks. Windows process/network calls are mocked.
$ErrorActionPreference = 'Stop'
$launcherTestState = @{ Scenario = 'fresh'; Launched = 0; Exe = (Join-Path (Split-Path $PSScriptRoot -Parent) 'KYS Finance Server.exe') }
function Test-Path { param($LiteralPath, $PathType) return $true }
function Get-CimInstance {
    param($ClassName, $Filter)
    if ($launcherTestState.Scenario -eq 'running') {
        [pscustomobject]@{ ExecutablePath = $launcherTestState.Exe }
    }
}
function Get-NetTCPConnection {
    param($LocalPort, $State, $ErrorAction)
    if ($launcherTestState.Scenario -eq 'occupied') { [pscustomobject]@{ LocalPort = 5000 } }
}
function Start-Process {
    param($FilePath, $WorkingDirectory, $WindowStyle, $RedirectStandardOutput, $RedirectStandardError, [switch]$PassThru)
    if ($WindowStyle -ne 'Hidden') { throw 'Server launch must be hidden.' }
    $launcherTestState.Launched++
    [pscustomobject]@{ Id = 12345 }
}
$launcher = Join-Path (Split-Path $PSScriptRoot -Parent) 'Start KYS Finance.ps1'
& $launcher
if ($launcherTestState.Launched -ne 1) { throw 'Fresh launch failed.' }
$launcherTestState.Scenario = 'running'
& $launcher
if ($launcherTestState.Launched -ne 1) { throw 'Duplicate launch was not prevented.' }
$launcherTestState.Scenario = 'occupied'
$rejected = $false
try { & $launcher } catch {
    if ($_.Exception.Message -notlike 'Port 5000 is already used*') { throw }
    $rejected = $true
}
if (-not $rejected -or $launcherTestState.Launched -ne 1) { throw 'Port conflict was not prevented.' }
Write-Host 'PASS: hidden launch, duplicate prevention, port conflict protection.'
