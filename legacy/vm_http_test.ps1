param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($root -notlike '*KYS-Test-20261009*') { throw 'Test harness must only run in the isolated VM test folder.' }
$cookies = New-Object Net.CookieContainer
function Request-App($path, $fields) {
    $req = [Net.HttpWebRequest]::Create('http://127.0.0.1:5000' + $path)
    $req.CookieContainer = $cookies
    $req.AllowAutoRedirect = $false
    $req.Timeout = 15000
    if ($fields) {
        $parts = @()
        foreach ($key in $fields.Keys) { $parts += ([Uri]::EscapeDataString($key) + '=' + [Uri]::EscapeDataString([string]$fields[$key])) }
        $bytes = [Text.Encoding]::UTF8.GetBytes(($parts -join '&'))
        $req.Method = 'POST'
        $req.ContentType = 'application/x-www-form-urlencoded'
        $req.ContentLength = $bytes.Length
        $stream = $req.GetRequestStream(); $stream.Write($bytes,0,$bytes.Length); $stream.Close()
    }
    $response = $req.GetResponse()
    try {
        $memory = New-Object IO.MemoryStream
        $stream = $response.GetResponseStream()
        $buffer = New-Object byte[] 8192
        while (($read = $stream.Read($buffer,0,$buffer.Length)) -gt 0) { $memory.Write($buffer,0,$read) }
        $bytes = $memory.ToArray(); $memory.Close(); $stream.Close()
        return New-Object PSObject -Property @{ Status=[int]$response.StatusCode; Bytes=$bytes; Text=[Text.Encoding]::UTF8.GetString($bytes) }
    } finally { $response.Close() }
}
function Token($html) { return [regex]::Match($html,'name="csrf_token" value="([^"]+)"').Groups[1].Value }
try {
    $health = Request-App '/health' $null
    if ($health.Text -notmatch '"ok"') { throw 'Health failed' }
    $page = Request-App '/login' $null
    $login = Request-App '/login' @{ csrf_token=(Token $page.Text); username='admin'; password='Admin@2026' }
    if ($login.Status -ne 302) { throw 'Login failed' }
    if (-not $VerifyOnly) {
        $ledger = Request-App '/transactions' $null
        if ($ledger.Text -match 'VMTEST-INCOME') { throw 'Test entries already exist. Use -VerifyOnly.' }
        foreach ($entry in @(@{kind='income'; group='Trade Income'; name='Security Service Income'; amount='1250'; ref='VMTEST-INCOME'}, @{kind='expense'; group='Operational Expenditure'; name='Office Expenditure'; amount='250'; ref='VMTEST-EXPENSE'})) {
            $path = '/transactions/new?kind=' + $entry.kind
            $form = Request-App $path $null
            $pattern = '<option value="([^"]+)"[^>]*>[^<]*' + [regex]::Escape($entry.name) + '</option>'
            $category = [regex]::Match($form.Text,$pattern).Groups[1].Value
            if (-not $category) { throw ('Category missing: ' + $entry.name) }
            $saved = Request-App $path @{ csrf_token=(Token $form.Text); kind=$entry.kind; group_name=$entry.group; category_id=$category; cash_date='2026-10-09'; reference=$entry.ref; description='Disposable Windows 7 VM test'; subtotal=$entry.amount; sscl='0'; vat='0' }
            if ($saved.Status -ne 302) { throw ('Save failed: ' + $entry.ref) }
        }
    }
    $ledger = Request-App '/transactions' $null
    if ($ledger.Text -notmatch 'VMTEST-INCOME' -or $ledger.Text -notmatch 'VMTEST-EXPENSE') { throw 'Saved entries not visible' }
    $query = '?type=monthly&start=2026-10-09&end=2026-10-09'
    $report = Request-App ('/reports' + $query) $null
    if ($report.Text -notmatch '1,250.00' -or $report.Text -notmatch '250.00' -or $report.Text -notmatch '1,000.00') { throw 'Report totals failed' }
    $export = Request-App ('/reports/export' + $query) $null
    if ($export.Bytes[0] -ne 80 -or $export.Bytes[1] -ne 75) { throw 'Excel export failed' }
    [IO.File]::WriteAllBytes((Join-Path $root 'vm-report.xlsx'),$export.Bytes)
    $result = 'PASS: Windows ' + [Environment]::OSVersion.Version + '; PowerShell ' + $PSVersionTable.PSVersion + '; health, login, income 1250, expense 250, P/L 1000, ledger, Excel. VerifyOnly=' + $VerifyOnly
    Set-Content -LiteralPath (Join-Path $root 'vm-test-result.txt') -Value $result
    Write-Output $result
    exit 0
} catch {
    $result = 'FAIL: ' + $_.Exception.Message
    Set-Content -LiteralPath (Join-Path $root 'vm-test-result.txt') -Value $result
    Write-Output $result
    exit 1
}
