import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from legacy.uninstall_gui import checked_manifest, remove_install

class UninstallTests(unittest.TestCase):
    def test_keep_data_default_and_purge_only_local_data(self):
        for purge in (False, True):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / 'installation'
                root.mkdir()
                (root / 'app.exe').write_text('test')
                (root / 'unrelated.txt').write_text('keep')
                for name in ('data', 'backups', 'restore-recovery'):
                    (root / name).mkdir()
                    (root / name / 'test.db').write_text('data')
                outside = Path(temporary) / 'external-backup.db'
                outside.write_text('external')
                (root / 'backup-target.txt').write_text(str(outside))
                (root / 'kys-install.json').write_text(json.dumps({'root': str(root), 'kind': 'server', 'files': ['app.exe']}))
                with patch('legacy.uninstall_gui.subprocess.run', return_value=Mock(returncode=0)):
                    remove_install(root, purge)
                self.assertFalse((root / 'app.exe').exists())
                self.assertEqual((root / 'data/test.db').exists(), not purge)
                self.assertTrue(outside.exists())
                self.assertTrue((root / 'unrelated.txt').exists())

    def test_manifest_escape_and_data_entries_rejected(self):
        for filename in ('../outside.exe', 'data/test.db', 'DATA/test.db'):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / 'kys-install.json').write_text(json.dumps({'root': str(root), 'kind': 'server', 'files': [filename]}))
                with self.assertRaises(ValueError):
                    checked_manifest(root)

    def test_stop_failure_keeps_application_and_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'app.exe').write_text('test')
            (root / 'kys-install.json').write_text(json.dumps({'root': str(root), 'kind': 'server', 'files': ['app.exe']}))
            with patch('legacy.uninstall_gui.subprocess.run', return_value=Mock(returncode=1, stderr='Could not stop')):
                with self.assertRaises(RuntimeError):
                    remove_install(root, True)
            self.assertTrue((root / 'app.exe').exists())

    def test_locked_executable_preserves_manifest_and_does_not_finalize(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exe = root / 'KYS Finance Server.exe'
            exe.write_text('test')
            manifest = root / 'kys-install.json'
            manifest.write_text(json.dumps({'root': str(root), 'kind': 'server', 'files': [exe.name]}))
            original = Path.unlink
            def locked(path, *args, **kwargs):
                if path == exe:
                    raise PermissionError('locked')
                return original(path, *args, **kwargs)
            with patch('legacy.uninstall_gui.subprocess.run', return_value=Mock(returncode=0)) as runner, patch.object(Path, 'unlink', locked), patch('legacy.uninstall_gui.time.sleep'):
                with self.assertRaisesRegex(RuntimeError, 'administrator'):
                    remove_install(root)
                self.assertEqual(runner.call_count, 1)
                self.assertTrue(manifest.exists())
