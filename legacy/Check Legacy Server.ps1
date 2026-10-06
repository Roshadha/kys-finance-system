$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$report = Join-Path $root 'compatibility-test.txt'
$lines = @('KYS legacy compatibility test', ('Time: ' + (Get-Date)), ('Windows: ' + [Environment]::OSVersion.VersionString), ('PowerShell: ' + $PSVersionTable.PSVersion), ('64-bit OS: ' + [Environment]::Is64BitOperatingSystem))
$client = New-Object Net.WebClient
try {
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try { $response = $client.DownloadString('http://127.0.0.1:5000/health'); $ready = $true; break } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ready -or $response -notmatch 'kys-finance' -or $response -notmatch '"ok"') { throw 'Server health check failed. Attach server-error.log and launcher-error.log.' }
    $login = $client.DownloadString('http://127.0.0.1:5000/login')
    if ($login -notmatch 'password') { throw 'Login page check failed.' }
    $lines += 'PASS: running server health and login page. This does NOT prove reboot startup or data-entry/export operation.'
    Start-Process 'http://127.0.0.1:5000/'
} catch { $lines += ('FAIL: ' + $_.Exception.Message) } finally {
    $client.Dispose()
    $lines | Set-Content -LiteralPath $report -Encoding UTF8
    $lines | ForEach-Object { Write-Host $_ }
}
