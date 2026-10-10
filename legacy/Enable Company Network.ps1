$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $argsText = '-NoProfile -ExecutionPolicy Bypass -File "' + $MyInvocation.MyCommand.Path + '"'
    $process = Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -Verb RunAs -WindowStyle Hidden -ArgumentList $argsText -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Firewall approval/setup failed. Setup is incomplete.' }
    exit 0
}
foreach ($rule in @(@('HTTP','TCP','5000'), @('Discovery','UDP','5057'))) {
    & netsh advfirewall firewall add rule ('name=KYS Company ' + $rule[0]) dir=in action=allow ('program=' + (Join-Path $root 'KYS Finance Server.exe')) ('protocol=' + $rule[1]) ('localport=' + $rule[2]) remoteip=LocalSubnet profile=private
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
