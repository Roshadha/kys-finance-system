import tempfile
import json
import os
import subprocess
import sys
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from legacy.setup_gui import validate_setup, extract_payload, run_install, run_logged_setup, repair_shortcuts


class SetupGuiTests(unittest.TestCase):
    def test_shortcut_locations_remain_compatible_with_windows_7(self):
        legacy = Path(__file__).resolve().parents[1] / 'legacy'
        shortcuts = (legacy / 'Create Company Shortcuts.ps1').read_text()
        installer = (legacy / 'Install Company Server.ps1').read_text()
        self.assertIn("Join-Path $env:PUBLIC 'Desktop'", shortcuts)
        self.assertIn("Join-Path $env:ProgramData 'Microsoft\\Windows\\Start Menu\\Programs\\Startup'", shortcuts)
        self.assertNotIn("$desktop = [Environment]::GetFolderPath('CommonDesktopDirectory')", shortcuts)
        self.assertNotIn("$startup = [Environment]::GetFolderPath('CommonStartup')", shortcuts)
        self.assertIn("throw 'Shared Desktop and Startup shortcut creation failed.'", installer)
        cleanup = (legacy / 'uninstall_cleanup.ps1').read_text()
        self.assertNotIn("GetFolderPath('CommonDesktopDirectory')", cleanup)
        self.assertNotIn("GetFolderPath('CommonStartup')", cleanup)

    def test_shortcut_repair_preserves_existing_company_data(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            (target / 'KYS Finance Server.exe').write_bytes(b'app')
            (target / 'data').mkdir()
            database = target / 'data' / 'kys_finance.db'
            database.write_bytes(b'company records')
            script = target / 'Create Company Shortcuts.ps1'
            script.write_text('test')
            with self.assertRaisesRegex(ValueError, 'recognized'):
                repair_shortcuts(str(target), script, lambda *args: None)
            (target / 'setup-complete.txt').write_text('Configured')
            with patch('legacy.setup_gui.run_logged_setup') as run:
                repair_shortcuts(str(target), script, lambda *args: None)
            self.assertEqual(database.read_bytes(), b'company records')
            self.assertEqual(run.call_args.args[1], target)
            self.assertIn('-InstallDirectory', run.call_args.args[0])
            self.assertEqual(run.call_args.args[0][-1], str(target))
            self.assertEqual(run.call_args.args[-1], 'shortcut-repair.log')

    def test_shortcut_repair_recovers_only_recognized_unfinished_server(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            (target / 'KYS Finance Server.exe').write_bytes(b'app')
            (target / 'company-installation.txt').write_text('Company setup')
            (target / 'kys-install.json').write_text(
                json.dumps({'kind': 'server', 'root': str(target)}))
            (target / 'data').mkdir()
            database = target / 'data' / 'kys_finance.db'
            database.write_bytes(b'company records')
            script = target / 'Create Company Shortcuts.ps1'
            with patch('legacy.setup_gui.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as check, patch('legacy.setup_gui.run_logged_setup') as run:
                repair_shortcuts(str(target), script, lambda *args: None)
            self.assertIn('--check-admin', check.call_args.args[0])
            self.assertTrue((target / 'setup-complete.txt').is_file())
            self.assertEqual(database.read_bytes(), b'company records')
            self.assertTrue(run.called)
            (target / 'setup-complete.txt').unlink()
            with patch('legacy.setup_gui.subprocess.run', return_value=subprocess.CompletedProcess([], 0)), patch('legacy.setup_gui.run_logged_setup', side_effect=RuntimeError('shortcut conflict')):
                with self.assertRaisesRegex(RuntimeError, 'shortcut conflict'):
                    repair_shortcuts(str(target), script, lambda *args: None)
            self.assertFalse((target / 'setup-complete.txt').exists())
            self.assertEqual(database.read_bytes(), b'company records')

    def test_setup_finishes_while_launched_server_keeps_output_open(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            helper = "import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(4)']); print('Setup complete', flush=True)"
            started = time.monotonic()
            try:
                run_logged_setup([sys.executable, '-c', helper], target, os.environ.copy())
                self.assertLess(time.monotonic() - started, 3)
                self.assertIn('Setup complete', (target / 'setup-install.log').read_text())
            finally:
                time.sleep(4.5)

    def test_credentials_and_existing_data_are_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'install'
            with self.assertRaises(ValueError):
                validate_setup(str(target), 'owner', 'short', 'short')
            self.assertEqual(validate_setup(str(target), 'owner', 'Six123', 'Six123'), target)
            with self.assertRaises(ValueError):
                validate_setup(str(target), 'owner', 'LongPassword123', 'different')
            target.mkdir()
            (target / 'company.db').write_bytes(b'keep')
            with self.assertRaises(ValueError):
                validate_setup(str(target), 'owner', 'LongPassword123', 'LongPassword123')
            self.assertEqual((target / 'company.db').read_bytes(), b'keep')

    def test_archive_traversal_and_data_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'install'
            for name in ('../outside.txt', 'data/kys_finance.db'):
                archive = Path(folder) / 'payload.zip'
                with zipfile.ZipFile(archive, 'w') as output:
                    output.writestr(name, b'unsafe')
                with self.assertRaises(ValueError):
                    extract_payload(archive, target)

    @patch('legacy.setup_gui.register_install')
    def test_install_credentials_use_stdin_and_permission_failure_can_retry(self, registration):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'install'
            archive = Path(folder) / 'payload.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('KYS Finance Server.exe', b'test')
            from subprocess import CompletedProcess
            def failed_permission(command, **options):
                if '--configure-admin-json' in command:
                    return CompletedProcess([], 0, '', '')
                options['stdout'].write(b'Permission denied')
                return CompletedProcess([], 1)
            with patch('legacy.setup_gui.subprocess.run', side_effect=failed_permission) as runner:
                with self.assertRaisesRegex(RuntimeError, 'Permission denied'):
                    run_install(str(target), 'owner', 'LongPassword123', archive, lambda *args: None)
                self.assertNotIn('LongPassword123', str(runner.call_args_list[0].args))
                self.assertIn('LongPassword123', runner.call_args_list[0].kwargs['input'])
                self.assertNotEqual(runner.call_args_list[1].kwargs['stdout'], -1)
            self.assertTrue((target / 'gui-setup-pending.txt').exists())
            with patch('legacy.setup_gui.subprocess.run', return_value=CompletedProcess([], 0, '', '')):
                run_install(str(target), 'owner', 'LongPassword123', archive, lambda *args: None)
            self.assertFalse((target / 'gui-setup-pending.txt').exists())
