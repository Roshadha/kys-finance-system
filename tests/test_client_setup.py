import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from client.setup_gui import install_client


@unittest.skipUnless(shutil.which('powershell.exe'), 'Windows shortcut integration')
class ClientSetupTests(unittest.TestCase):
    @patch('client.setup_gui.register_install')
    def test_installs_shortcuts_preserves_server_choice_and_can_repeat(self, registration):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target, desktop, startup = [root / name for name in ('client', 'desktop', 'startup')]
            for directory in (target, desktop, startup):
                directory.mkdir()
            saved = '{"address":"192.168.1.5","port":5000,"manual":true}'
            (target / 'server.json').write_text(saved)
            resources = Path(__file__).resolve().parents[1] / 'client'
            for attempt in range(2):
                install_client(resources, target, desktop, startup, skip_monitor=True)
                self.assertEqual((target / 'server.json').read_text(), saved)
                self.assertTrue((desktop / 'KYS Finance.lnk').is_file())
                self.assertTrue((startup / 'KYS Finance Client Discovery.lnk').is_file())
                self.assertFalse((target / 'data').exists())
            environment = dict(os.environ, KYS_CLIENT_TEST=str(target), KYS_DESKTOP_TEST=str(desktop), KYS_STARTUP_TEST=str(startup))
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', """
$shell = New-Object -ComObject WScript.Shell
$desktop = $shell.CreateShortcut((Join-Path $env:KYS_DESKTOP_TEST 'KYS Finance.lnk'))
$startup = $shell.CreateShortcut((Join-Path $env:KYS_STARTUP_TEST 'KYS Finance Client Discovery.lnk'))
if ($desktop.WorkingDirectory -ne $env:KYS_CLIENT_TEST) { throw 'Wrong desktop target' }
if ($startup.Arguments -notlike '*-Mode Monitor') { throw 'Missing startup discovery' }
if ($desktop.Arguments -notlike '*KYS Client.ps1*') { throw 'Missing launcher' }
"""], env=environment, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
