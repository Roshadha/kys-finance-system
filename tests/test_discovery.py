import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from discovery import discovery_reply, start_discovery


class DiscoveryTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("powershell.exe"), "Windows shortcut integration")
    def test_windows_shortcut_points_to_discovering_launcher(self):
        with tempfile.TemporaryDirectory(prefix="kys client test ") as folder:
            env = dict(os.environ, KYS_TEST_SHORTCUT=folder,
                       KYS_TEST_CLIENT=str(Path(__file__).resolve().parents[1] / "client" / "KYS Client.ps1"))
            command = r'''
$ErrorActionPreference = 'Stop'
. $env:KYS_TEST_CLIENT -FunctionsOnly
New-KysShortcut -ShortcutDirectory $env:KYS_TEST_SHORTCUT
$link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $env:KYS_TEST_SHORTCUT 'KYS Finance.lnk'))
if ($link.Arguments -notlike ('*"' + $env:KYS_TEST_CLIENT + '"*')) { throw 'Launcher path was not quoted correctly' }
if ($link.TargetPath -notlike '*powershell.exe') { throw 'Wrong shortcut target' }
'''
            result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                                    env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((Path(folder) / "KYS Finance.lnk").exists())

    def test_valid_request_and_invalid_inputs(self):
        request = {"service": "kys-finance", "version": 1, "nonce": "a" * 32}
        data = json.dumps(request).encode()
        reply = json.loads(discovery_reply(data, "192.168.1.4", 5000, "OFFICE"))
        self.assertEqual(reply, dict(request, name="OFFICE", port=5000))
        self.assertIsNone(discovery_reply(data, "8.8.8.8", 5000, "OFFICE"))
        for bad in [b"bad", b"[]", b"null", b"\xff", b"{}",
                    json.dumps(dict(request, nonce="wrong")).encode(),
                    json.dumps(dict(request, version=2)).encode(),
                    json.dumps(dict(request, service="other")).encode()]:
            self.assertIsNone(discovery_reply(bad, "127.0.0.1", 5000, "OFFICE"))

    def test_udp_roundtrip_and_shutdown(self):
        stopped, thread, port = start_discovery(5001, "127.0.0.1", 0)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(2)
                request = {"service": "kys-finance", "version": 1, "nonce": "b" * 32}
                client.sendto(json.dumps(request).encode(), ("127.0.0.1", port))
                reply = json.loads(client.recvfrom(2048)[0])
                self.assertEqual(reply["nonce"], request["nonce"])
                self.assertEqual(reply["port"], 5001)
        finally:
            stopped.set()
            thread.join(2)
        self.assertFalse(thread.is_alive())

    @unittest.skipUnless(shutil.which("powershell.exe"), "Windows PowerShell integration")
    def test_actual_windows_client_discovers_and_checks_http(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"service":"kys-finance","status":"ok"}')

            def log_message(self, *args):
                pass

        http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=http.serve_forever, daemon=True)
        worker.start()
        stopped, thread, port = start_discovery(http.server_port, "127.0.0.1", 0)
        env = dict(os.environ, KYS_TEST_CLIENT=str(Path(__file__).resolve().parents[1] / "client" / "KYS Client.ps1"),
                   KYS_TEST_PORT=str(port))
        command = r'''
$ErrorActionPreference = 'Stop'
. $env:KYS_TEST_CLIENT -FunctionsOnly
function Get-KysBroadcasts { '127.0.0.1' }
$servers = @(Find-KysServers -DiscoveryPort ([int]$env:KYS_TEST_PORT))
if ($servers.Count -ne 1) { throw 'Expected one discovered HTTP-verified server' }
$one = Select-KysServer $servers $null
if (-not $one) { throw 'Single server was not selected' }
$other = [pscustomobject]@{name='OTHER';address='127.0.0.2';port=5000}
if (Select-KysServer @($one, $other) $null) { throw 'Must not guess between multiple servers' }
if ((Select-KysServer @($one, $other) $one).name -ne $one.name) { throw 'Saved server selection failed' }
if (Select-KysServer @($other) $one) { throw 'Must not silently switch to another company server' }
if (Select-KysServer @($one) ([pscustomobject]@{manual=$true})) { throw 'Manual choice must not be replaced automatically' }
if (Test-KysServer 'invalid/address' 5000) { throw 'Invalid address accepted' }
$one | ConvertTo-Json -Compress
'''
        try:
            result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                                    env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            reply = json.loads(result.stdout)
            self.assertEqual(reply["address"], "127.0.0.1")
            self.assertEqual(reply["port"], http.server_port)
        finally:
            stopped.set()
            thread.join(2)
            http.shutdown()
            http.server_close()
            worker.join(2)
