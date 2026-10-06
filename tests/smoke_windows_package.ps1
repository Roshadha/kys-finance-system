param([Parameter(Mandatory=$true)][string]$PackageDirectory, [int]$Port = 5098)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$testDirectory = Join-Path $root ('tmp\package-smoke-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PackageDirectory 'KYS Finance Server.exe') -Destination $testDirectory
Copy-Item -LiteralPath (Join-Path $PackageDirectory '_internal') -Destination $testDirectory -Recurse
$env:PORT = "$Port"
$env:KYS_HOST = '127.0.0.1'
$env:KYS_DATABASE_URL = 'sqlite:///:memory:'
$env:KYS_SECRET_KEY = 'isolated-package-test'
$env:KYS_DISABLE_BACKUP = '1'
$process = Start-Process -FilePath (Join-Path $testDirectory 'KYS Finance Server.exe') -WorkingDirectory $testDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $testDirectory 'stdout.log') -RedirectStandardError (Join-Path $testDirectory 'stderr.log')
try {
    $ready = $false
    for ($i=0; $i -lt 60; $i++) {
        if ($process.HasExited) { throw (Get-Content (Join-Path $testDirectory 'stderr.log') -Raw) }
        try {
            $health = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2
            if ($health.status -eq 'ok' -and $health.service -eq 'kys-finance') { $ready=$true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'Health timeout' }
    $login = Invoke-WebRequest "http://127.0.0.1:$Port/login" -UseBasicParsing
    if ($login.StatusCode -ne 200 -or $login.Content -notmatch 'password') { throw 'Login page failed' }
    $binary = [IO.File]::OpenRead((Join-Path $testDirectory 'KYS Finance Server.exe'))
    $reader = New-Object IO.BinaryReader($binary)
    try {
        $binary.Position = 60
        $offset = $reader.ReadInt32()
        $binary.Position = $offset + 4
        $machine = $reader.ReadUInt16()
    } finally { $reader.Dispose() }
    Write-Host ('PASS: health + login; PE machine = 0x{0:X4}' -f $machine)
} finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
