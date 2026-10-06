$ErrorActionPreference = 'Stop'
$testState = @{ Enabled = $false; Registered = $false; Foreign = $false }
function Test-Path { param($LiteralPath, $PathType) return $true }
function Import-Module { param($Name, $ErrorAction) }
function Get-ScheduledTask {
    param($TaskName, $ErrorAction)
    if ($testState.Foreign) { [pscustomobject]@{ Actions = [pscustomobject]@{ Execute = 'C:\other.exe'; Arguments = '' } } }
}
function New-ScheduledTaskAction { param($Execute,$Argument,$WorkingDirectory) return @{ Execute=$Execute; Arguments=$Argument } }
function New-ScheduledTaskTrigger { param([switch]$AtLogOn,$User) return [pscustomobject]@{ Delay=''; User=$User } }
function New-ScheduledTaskPrincipal { param($UserId,$LogonType,$RunLevel) return @{ User=$UserId } }
function New-ScheduledTaskSettingsSet {
    param($RestartCount,$RestartInterval,$ExecutionTimeLimit,$MultipleInstances,[switch]$StartWhenAvailable,[switch]$DontStopIfGoingOnBatteries,[switch]$AllowStartIfOnBatteries)
    if ($RestartCount -ne 10 -or $ExecutionTimeLimit.TotalSeconds -ne 0 -or $MultipleInstances -ne 'IgnoreNew') { throw 'Wrong task settings' }
    return @{}
}
function Register-ScheduledTask {
    param($TaskName,$Action,$Trigger,$Principal,$Settings,$Description,[switch]$Force,$ErrorAction)
    if ($Trigger.Delay -ne 'PT30S' -or $Action.Arguments -notlike '*-WaitForExit') { throw 'Wrong launch settings' }
    $testState.Registered = $true
}
function Enable-ScheduledTask { param($TaskName,$ErrorAction) $testState.Enabled = $true }
$scriptPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'Enable Auto Start.ps1'
$result = & $scriptPath
if (-not $testState.Enabled -or -not $testState.Registered -or $result.Mode -ne 'Task') { throw 'Registration failed' }
$testState.Foreign = $true
$blocked = $false
try { & $scriptPath } catch { if ($_.Exception.Message -like 'A different task already uses*') { $blocked = $true } else { throw } }
if (-not $blocked) { throw 'Foreign task overwritten' }
Write-Host 'PASS: delayed logon, retries, enable disabled task, registration result, foreign task protection.'
