import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

os.environ['KYS_DISABLE_BACKUP'] = '1'

from sqlalchemy import create_engine
from app import migrate_integer_ids


LEGACY_SCHEMA = '''
CREATE TABLE user (id INTEGER PRIMARY KEY, username TEXT, password_hash TEXT);
CREATE TABLE vehicle (id INTEGER PRIMARY KEY, identifier TEXT);
CREATE TABLE "group" (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
 active BOOLEAN NOT NULL, UNIQUE(kind, name));
CREATE TABLE category (id INTEGER PRIMARY KEY, code TEXT, kind TEXT NOT NULL,
 group_name TEXT NOT NULL, name TEXT NOT NULL, service_line TEXT, entity_name TEXT, active BOOLEAN NOT NULL);
CREATE TABLE "transaction" (id INTEGER PRIMARY KEY, cash_date DATE NOT NULL,
 category_id INTEGER NOT NULL REFERENCES category(id), vehicle_id INTEGER REFERENCES vehicle(id),
 reference TEXT NOT NULL, counterparty TEXT NOT NULL, description TEXT, subtotal NUMERIC NOT NULL,
 sscl NUMERIC NOT NULL, vat NUMERIC NOT NULL, total NUMERIC NOT NULL,
 created_by_id INTEGER NOT NULL REFERENCES user(id), created_at DATETIME NOT NULL);
CREATE TABLE adjustment (id INTEGER PRIMARY KEY, transaction_id INTEGER NOT NULL REFERENCES "transaction"(id),
 effective_date DATE NOT NULL, amount NUMERIC NOT NULL, reason TEXT NOT NULL,
 created_by_id INTEGER NOT NULL REFERENCES user(id), created_at DATETIME NOT NULL);
CREATE TABLE audit_log (id INTEGER PRIMARY KEY, happened_at DATETIME NOT NULL,
 user_id INTEGER REFERENCES user(id), action TEXT NOT NULL, entity_type TEXT NOT NULL,
 entity_id INTEGER, details TEXT);
INSERT INTO user VALUES (1, 'existing-user', 'keep-this-hash');
INSERT INTO vehicle VALUES (1, 'existing-vehicle');
INSERT INTO "group" VALUES (7, 'income', 'Trade Income', 1), (9, 'expense', 'Operational Expenditure', 0);
INSERT INTO category VALUES (12, '351', 'income', 'Trade Income', 'Security Service Income', 'Security', NULL, 1),
 (27, '501', 'expense', 'Operational Expenditure', 'Office Expenditure', NULL, NULL, 0),
 (28, '351', 'income', 'Legacy custom group', 'Custom Income', NULL, NULL, 1);
INSERT INTO "transaction" VALUES (5, '2026-09-01', 12, NULL, 'REF-I', 'Customer', 'keep description',
 1000.25, 25, 150, 1175.25, 1, '2026-09-01 10:00:00'),
 (8, '2026-09-02', 27, 1, 'REF-E', 'Supplier', NULL, 400.50, 0, 0, 400.50, 1, '2026-09-02 10:00:00');
INSERT INTO adjustment VALUES (3, 5, '2026-09-03', -50.25, 'keep correction', 1, '2026-09-03 10:00:00');
INSERT INTO audit_log VALUES (1, '2026-09-01 10:00:00', 1, 'create', 'category', 12, 'keep category audit'),
 (2, '2026-09-01 10:00:00', 1, 'create', 'group', 7, 'keep group audit'),
 (3, '2026-09-01 10:00:00', 1, 'create', 'transaction', 5, 'keep transaction audit');
'''


class AccountMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kys-migration-')
        self.root = Path(self.temp.name)
        self.path = self.root / 'finance.db'
        self.backups = self.root / 'backups'
        self.con = sqlite3.connect(self.path)
        self.con.execute('PRAGMA journal_mode=WAL')
        self.con.executescript(LEGACY_SCHEMA)
        self.con.commit()
        self.engine = create_engine('sqlite:///' + self.path.as_posix())

    def tearDown(self):
        self.con.close()
        self.engine.dispose()
        self.temp.cleanup()

    def test_preserves_money_links_audit_and_legacy_codes(self):
        before = self.con.execute('SELECT * FROM "transaction" ORDER BY id').fetchall()
        adjustments = self.con.execute('SELECT * FROM adjustment').fetchall()
        migrate_integer_ids(self.engine, self.backups)
        after = self.con.execute('SELECT * FROM "transaction" ORDER BY id').fetchall()
        for original, updated in zip(before, after):
            self.assertEqual(original[:2] + original[3:], updated[:2] + updated[3:])
        self.assertEqual(len(before), len(after))
        self.assertEqual([r[2] for r in after], ['IP_0010', 'EP_0010'])
        self.assertEqual(self.con.execute('SELECT * FROM adjustment').fetchall(), adjustments)
        self.assertEqual(self.con.execute('SELECT password_hash FROM user').fetchone()[0], 'keep-this-hash')
        self.assertEqual(self.con.execute('SELECT identifier FROM vehicle').fetchone()[0], 'existing-vehicle')
        self.assertEqual(self.con.execute('SELECT active FROM category WHERE id="EP_0010"').fetchone()[0], 0)
        self.assertEqual(self.con.execute('SELECT entity_id FROM audit_log ORDER BY id').fetchall(),
                         [('IP_0010',), ('IG_100',), ('5',)])
        self.assertEqual(self.con.execute('SELECT legacy_code FROM account_code_migration WHERE old_id="12" AND entity_type="category"').fetchone()[0], '351')
        self.assertFalse(self.con.execute('PRAGMA foreign_key_check').fetchall())
        self.assertEqual(self.con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertIsNotNone(self.con.execute('SELECT group_id FROM category WHERE id="IP_0020"').fetchone()[0])
        backup = next(self.backups.glob('pre-code-migration-*.db'))
        with closing(sqlite3.connect(backup)) as copy:
            # WAL contents and pre-migration integer IDs must be in the snapshot.
            self.assertEqual(copy.execute('SELECT * FROM "transaction" ORDER BY id').fetchall(), before)
            self.assertEqual(copy.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_second_start_does_not_renumber_or_repeat_backup(self):
        migrate_integer_ids(self.engine, self.backups)
        first = list(self.con.iterdump())
        migrate_integer_ids(self.engine, self.backups)
        self.assertEqual(list(self.con.iterdump()), first)
        self.assertEqual(len(list(self.backups.glob('*.db'))), 1)

    def test_ddl_failure_rolls_back_original_database(self):
        original = list(self.con.iterdump())
        with patch('app.CreateTable', side_effect=RuntimeError('simulated failure')):
            with self.assertRaisesRegex(RuntimeError, 'simulated failure'):
                migrate_integer_ids(self.engine, self.backups)
        self.assertEqual(list(self.con.iterdump()), original)
        self.assertEqual(len(list(self.backups.glob('*.db'))), 1)

    def test_broken_reference_does_not_leave_a_partial_upgrade(self):
        self.con.execute('UPDATE "transaction" SET created_by_id=999 WHERE id=5')
        self.con.commit()
        original = list(self.con.iterdump())
        with self.assertRaisesRegex(RuntimeError, 'broken data reference'):
            migrate_integer_ids(self.engine, self.backups)
        self.assertEqual(list(self.con.iterdump()), original)
