import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
from werkzeug.security import generate_password_hash
from backup_restore import authenticate, inspect_backup, restore_database, migrate_staged_backup


class RestoreTests(unittest.TestCase):
    def test_newer_backup_is_rejected_without_changing_live_data(self):
        with closing(sqlite3.connect(str(self.backup))) as connection:
            connection.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(ValueError, 'newer'):
            migrate_staged_backup(self.backup, self.live)
        self.assertEqual(self.amount(self.live), 10)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        self.live = self.root / 'data' / 'kys_finance.db'
        self.backup = self.root / 'old.db'
        self.secret = self.root / 'data' / '.secret_key'
        self.secret.write_text('original-session-secret')
        for file, amount in ((self.live, 10), (self.backup, 999)):
            with closing(sqlite3.connect(str(file))) as connection:
                connection.executescript('CREATE TABLE user (username TEXT, password_hash TEXT, role TEXT, active INTEGER); CREATE TABLE "transaction" (cash_date TEXT, amount INTEGER);')
                connection.execute('INSERT INTO user VALUES (?,?,?,?)', ('owner', generate_password_hash('OwnerPassword123'), 'admin', 1))
                connection.execute('INSERT INTO "transaction" VALUES (?,?)', ('2026-10-12', amount))
                connection.commit()

    def amount(self, path):
        with closing(sqlite3.connect(str(path))) as con:
            return con.execute('SELECT amount FROM "transaction"').fetchone()[0]

    def test_preview_auth_safety_copy_and_restore(self):
        self.assertEqual(inspect_backup(self.backup, self.live), (1, '2026-10-12'))
        self.assertFalse(authenticate(self.live, 'owner', 'wrong'))
        self.assertTrue(authenticate(self.live, 'OWNER', 'OwnerPassword123'))
        recovery = restore_database(self.backup, self.root)
        self.assertEqual(self.amount(self.live), 999)
        self.assertEqual(self.amount(recovery / 'kys_finance.db'), 10)
        self.assertEqual((recovery / '.secret_key').read_text(), 'original-session-secret')
        self.assertNotEqual(self.secret.read_text(), 'original-session-secret')

    def test_invalid_or_incompatible_backup_keeps_live_data(self):
        self.backup.write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            restore_database(self.backup, self.root)
        self.assertEqual(self.amount(self.live), 10)

    def test_no_admin_is_rejected(self):
        with closing(sqlite3.connect(str(self.backup))) as con:
            con.execute('UPDATE user SET active=0')
            con.commit()
        with self.assertRaisesRegex(ValueError, 'administrator'):
            restore_database(self.backup, self.root)
        self.assertEqual(self.amount(self.live), 10)

    def test_known_old_schema_migrates_staged_copy_only(self):
        import shutil
        with closing(sqlite3.connect(str(self.live))) as con:
            con.execute('ALTER TABLE user ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT 0')
            con.commit()
        staged = self.root / 'staged.db'
        shutil.copy2(self.backup, staged)
        migrate_staged_backup(staged, self.live)
        self.assertEqual(inspect_backup(staged, self.live)[0], 1)
        with closing(sqlite3.connect(str(self.backup))) as con:
            self.assertNotIn('deleted', {r[1] for r in con.execute('PRAGMA table_info(user)')})

    def test_secret_write_failure_rolls_back_database(self):
        with patch('backup_restore.os.replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                restore_database(self.backup, self.root)
        self.assertEqual(self.amount(self.live), 10)
        self.assertEqual(self.secret.read_text(), 'original-session-secret')
