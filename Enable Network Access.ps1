param([int]$Port = 5000)
$ErrorActionPreference = 'Stop'
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Invalid HTTP port.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -Port ' + $Port
    $process = Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Network setup failed in the elevated process. Run this script as administrator to see the error.' }
    Write-Host 'KYS Finance network access enabled. Set the trusted company connection to Private in Windows network settings.'
    exit 0
}
$exe = Join-Path $PSScriptRoot 'KYS Finance Server.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Run this helper from the installed KYS Finance Server folder.' }
foreach ($rule in @(@{Name='KYS Finance HTTP'; Protocol='TCP'; Port=$Port}, @{Name='KYS Finance Discovery'; Protocol='UDP'; Port=5057})) {
    $existing = Get-NetFirewallRule -Name $rule.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Set-NetFirewallRule -Name $rule.Name -Direction Inbound -Action Allow -Enabled True -Profile Private -Program $exe -Protocol $rule.Protocol -LocalPort $rule.Port -RemoteAddress LocalSubnet | Out-Null
    } else {
        New-NetFirewallRule -Name $rule.Name -DisplayName $rule.Name -Direction Inbound -Action Allow -Enabled True -Profile Private -Program $exe -Protocol $rule.Protocol -LocalPort $rule.Port -RemoteAddress LocalSubnet | Out-Null
    }
}
Write-Host 'KYS Finance network access enabled on Private networks for the local subnet.'
