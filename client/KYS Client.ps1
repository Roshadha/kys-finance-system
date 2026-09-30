param(
    [ValidateSet('Open', 'Monitor')][string]$Mode = 'Open',
    [switch]$FunctionsOnly
)
$ErrorActionPreference = 'Stop'
$script:ClientDirectory = $PSScriptRoot
$script:ConfigPath = Join-Path $script:ClientDirectory 'server.json'

function New-KysShortcut([string]$ShortcutDirectory = [Environment]::GetFolderPath('Desktop')) {
    $link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $ShortcutDirectory 'KYS Finance.lnk'))
    $link.TargetPath = Join-Path $PSHOME 'powershell.exe'
    $link.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $script:ClientDirectory 'KYS Client.ps1') + '"'
    $link.WorkingDirectory = $script:ClientDirectory
    $link.Description = 'Find the KYS Finance server on the company network and open it'
    $link.Save()
}

function Test-KysServer([string]$Address, [int]$Port) {
    if ($Address -notmatch '^[A-Za-z0-9.-]+$' -or $Port -lt 1 -or $Port -gt 65535) { return $false }
    $response = $null
    try {
        $request = [Net.HttpWebRequest]::Create("http://${Address}:${Port}/health")
        $request.Proxy = $null
        $request.Timeout = 1500
        $request.ReadWriteTimeout = 1500
        $request.AllowAutoRedirect = $false
        $response = $request.GetResponse()
        $reader = New-Object IO.StreamReader($response.GetResponseStream())
        try { $health = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
        return ($health.service -eq 'kys-finance' -and $health.status -eq 'ok')
    } catch { return $false } finally { if ($response) { $response.Close() } }
}

function Get-KysBroadcasts {
    $addresses = @('255.255.255.255')
    foreach ($adapter in [Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces()) {
        if ($adapter.OperationalStatus -ne 'Up' -or $adapter.NetworkInterfaceType -eq 'Loopback') { continue }
        foreach ($unicast in $adapter.GetIPProperties().UnicastAddresses) {
            if ($unicast.Address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) { continue }
            $ip = $unicast.Address.GetAddressBytes()
            $mask = $unicast.IPv4Mask.GetAddressBytes()
            $broadcast = for ($i = 0; $i -lt 4; $i++) { $ip[$i] -bor (255 -bxor $mask[$i]) }
            $addresses += $broadcast -join '.'
        }
    }
    return $addresses | Select-Object -Unique
}

function Find-KysServers([int]$DiscoveryPort = 5057) {
    $udp = New-Object Net.Sockets.UdpClient
    $found = @{}
    try {
        $udp.EnableBroadcast = $true
        $udp.Client.ReceiveTimeout = 400
        $nonce = [Guid]::NewGuid().ToString('N')
        $packet = [Text.Encoding]::UTF8.GetBytes((@{service='kys-finance'; version=1; nonce=$nonce} | ConvertTo-Json -Compress))
        foreach ($address in Get-KysBroadcasts) {
            try { [void]$udp.Send($packet, $packet.Length, $address, $DiscoveryPort) } catch { }
        }
        $deadline = [DateTime]::UtcNow.AddSeconds(3)
        while ([DateTime]::UtcNow -lt $deadline) {
            try {
                $peer = New-Object Net.IPEndPoint([Net.IPAddress]::Any, 0)
                $data = $udp.Receive([ref]$peer)
                if ($data.Length -gt 2048) { continue }
                $reply = [Text.Encoding]::UTF8.GetString($data) | ConvertFrom-Json
                if ($reply.service -ne 'kys-finance' -or $reply.version -ne 1 -or $reply.nonce -cne $nonce) { continue }
                $port = 0
                if (-not [int]::TryParse([string]$reply.port, [ref]$port) -or $port -lt 1 -or $port -gt 65535) { continue }
                $address = $peer.Address.ToString()
                $name = [string]$reply.name -replace '[^A-Za-z0-9_.-]', ''
                $name = $name.Substring(0, [Math]::Min(63, $name.Length))
                if (-not $name -or $found.Count -ge 16) { continue }
                $found["${address}:$port"] = [pscustomobject]@{address=$address; port=$port; name=$name; manual=$false}
            } catch [Net.Sockets.SocketException] { } catch [ArgumentException] { } catch { }
        }
    } finally { $udp.Close() }
    foreach ($server in $found.Values) {
        if (Test-KysServer $server.address $server.port) { $server }
    }
}

function Get-KysSavedServer {
    try { return Get-Content -LiteralPath $script:ConfigPath -Raw | ConvertFrom-Json } catch { return $null }
}

function Save-KysServer($Server) {
    $temporary = Join-Path $script:ClientDirectory ([Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        $Server | ConvertTo-Json | Set-Content -LiteralPath $temporary -Encoding UTF8
        Move-Item -LiteralPath $temporary -Destination $script:ConfigPath -Force
    } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
}

function Select-KysServer($Servers, $Saved) {
    $list = @($Servers)
    if ($Saved -and $Saved.manual) { return $null }
    if ($Saved -and -not $Saved.manual) {
        $preferred = @($list | Where-Object { $_.name -eq $Saved.name })
        if ($preferred.Count -eq 1) { return $preferred[0] }
        return $null
    }
    if ($list.Count -eq 1) { return $list[0] }
    return $null
}

if ($FunctionsOnly) { return }
if ($Mode -eq 'Monitor') {
    # One watcher per signed-in user; no browser is opened automatically.
    $mutex = New-Object Threading.Mutex($false, 'Local\KYSFinanceClientDiscovery')
    try { $acquired = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { $mutex.Dispose(); exit }
    try {
        while ($true) {
            try {
                $saved = Get-KysSavedServer
                $server = Select-KysServer @(Find-KysServers) $saved
                if ($saved -and $saved.manual -and (Test-KysServer $saved.address $saved.port)) { $server = $saved }
                if ($server) { Save-KysServer $server; New-KysShortcut; break }
            } catch { }
            Start-Sleep -Seconds 30
        }
    } finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
    exit
}

try {
    Write-Host 'Looking for KYS Finance on your company Wi-Fi/LAN...'
    $saved = Get-KysSavedServer
    $servers = @(Find-KysServers)
    $server = Select-KysServer $servers $saved
    if ($saved -and $saved.manual -and (Test-KysServer $saved.address $saved.port)) { $server = $saved }
    while (-not $server) {
        if ($servers.Count -gt 0) {
            Write-Host 'Choose the company server:'
            for ($i = 0; $i -lt $servers.Count; $i++) {
                Write-Host ("{0}. {1} ({2}:{3})" -f ($i + 1), $servers[$i].name, $servers[$i].address, $servers[$i].port)
            }
        } else {
            Write-Host 'Server not found. Check it is running, both PCs use the company network, and server network access is enabled.'
        }
        $choice = Read-Host 'Enter server number, R to retry, M for a manual address, or Q to close'
        if ($choice -eq 'Q') { exit }
        if ($choice -eq 'R') {
            $servers = @(Find-KysServers)
            $server = Select-KysServer $servers $saved
            continue
        }
        if ($choice -eq 'M') {
            $address = Read-Host 'Server LAN IP or computer name (without http://)'
            $portText = Read-Host 'Port (Enter for 5000)'
            $port = 5000
            if ($portText -and -not [int]::TryParse($portText, [ref]$port)) { continue }
            if (Test-KysServer $address $port) {
                $server = [pscustomobject]@{address=$address; port=$port; name=$address; manual=$true}
            } else { Write-Host 'Cannot reach a compatible KYS Finance server at that address.' }
            continue
        }
        $index = 0
        if ([int]::TryParse($choice, [ref]$index) -and $index -ge 1 -and $index -le $servers.Count) { $server = $servers[$index - 1] }
    }
    Save-KysServer $server
    Start-Process ("http://{0}:{1}/" -f $server.address, $server.port)
} catch {
    Write-Host "Could not open KYS Finance: $($_.Exception.Message)"
    [void](Read-Host 'Press Enter to close')
    exit 1
}
