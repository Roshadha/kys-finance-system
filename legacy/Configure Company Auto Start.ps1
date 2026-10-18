param([string]$TaskName = 'KYS Finance Server')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $root 'Start Company Server.ps1'
if (-not (Test-Path -LiteralPath $startScript)) { throw 'Server start script is missing.' }

# Task Scheduler 2.0 is available on Windows 7. InteractiveToken needs no
# stored Windows password and retains access to this user's network shares.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$user = $identity.User.Value
$arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $startScript + '"'
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not (Test-Path -LiteralPath $powershell)) { throw 'Windows PowerShell is missing.' }
$service = New-Object -ComObject 'Schedule.Service'
$service.Connect()
$folder = $service.GetFolder('\')
$existing = $null
try { $existing = $folder.GetTask($TaskName) } catch { }
if ($existing) {
    if ($existing.Definition.Actions.Count -ne 1) {
        throw 'An auto-start task with this name belongs to another installation.'
    }
    $action = $existing.Definition.Actions.Item(1)
    $registeredUser = $existing.Definition.Principal.UserId
    try {
        $registeredSid = (New-Object Security.Principal.NTAccount($registeredUser)).Translate([Security.Principal.SecurityIdentifier]).Value
    } catch {
        $registeredSid = $registeredUser
    }
    if ($action.Type -ne 0 -or $action.Arguments -cne $arguments -or
        $registeredSid -ine $user) {
        throw 'An auto-start task with this name belongs to another installation or Windows user.'
    }
}

$definition = $service.NewTask(0)
$definition.RegistrationInfo.Description = 'Start the K.Y.S. Finance server immediately after this Windows user signs in.'
$definition.Principal.UserId = $user
$definition.Principal.LogonType = 3  # TASK_LOGON_INTERACTIVE_TOKEN
$definition.Principal.RunLevel = 0   # TASK_RUNLEVEL_LUA
$definition.Settings.Enabled = $true
$definition.Settings.StartWhenAvailable = $true
$definition.Settings.DisallowStartIfOnBatteries = $false
$definition.Settings.StopIfGoingOnBatteries = $false
$definition.Settings.MultipleInstances = 2  # Ignore a duplicate trigger.
$definition.Settings.ExecutionTimeLimit = 'PT2M'
$trigger = $definition.Triggers.Create(9)  # TASK_TRIGGER_LOGON
$trigger.UserId = $user
$trigger.Enabled = $true
$action = $definition.Actions.Create(0)  # TASK_ACTION_EXEC
$action.Path = $powershell
$action.Arguments = $arguments
$action.WorkingDirectory = $root
$folder.RegisterTaskDefinition($TaskName, $definition, 6, $user, $null, 3, $null) | Out-Null

$registered = $folder.GetTask($TaskName)
if (-not $registered.Enabled -or $registered.Definition.Triggers.Item(1).Type -ne 9 -or
    $registered.Definition.Actions.Item(1).Arguments -cne $arguments -or
    $registered.Definition.Actions.Item(1).Path -ine $powershell) {
    throw 'Windows did not register the KYS sign-in task correctly.'
}
Write-Host ('Immediate sign-in auto-start registered for ' + $identity.Name + '.')
