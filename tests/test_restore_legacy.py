import os
import sqlite3
import tempfile
from pathlib import Path
from unittest import TestCase
from contextlib import closing
from tests.test_account_migration import LEGACY_SCHEMA
from app import create_app, db
from backup_restore import migrate_staged_backup
from unittest.mock import patch
import app as finance

class LegacyRestoreTests(TestCase):
    def test_integer_id_backup_is_migrated_without_reentering_transactions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            current=root/'current.db'
            staged=root/'selected.db'
            with patch.object(finance,'DATA_ROOT',root):
                application=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite:///'+current.as_posix()})
                with application.app_context():
                    db.session.remove();db.engine.dispose()
            with closing(sqlite3.connect(staged)) as connection, closing(sqlite3.connect(current)) as target:
                connection.executescript(LEGACY_SCHEMA)
                # Use the supported legacy account tables with a complete user/vehicle schema.
                connection.execute('DROP TABLE user')
                connection.execute(target.execute("SELECT sql FROM sqlite_master WHERE name='user'").fetchone()[0])
                connection.execute("INSERT INTO user VALUES (1,'owner','Owner','Accounts','unchanged-hash','admin','[]',1,0,'2026-01-01')")
                connection.execute('DROP TABLE vehicle')
                connection.execute(target.execute("SELECT sql FROM sqlite_master WHERE name='vehicle'").fetchone()[0])
                connection.execute("INSERT INTO vehicle VALUES (1,'vehicle',NULL,NULL,1)")
                adjustments=connection.execute('SELECT * FROM adjustment').fetchall()
                connection.execute('DROP TABLE adjustment')
                connection.execute(target.execute("SELECT sql FROM sqlite_master WHERE name='adjustment'").fetchone()[0])
                connection.executemany('INSERT INTO adjustment VALUES (?,?,?,?,?,?,?)',adjustments)
                connection.commit()
                before=connection.execute('SELECT id,total FROM "transaction" ORDER BY id').fetchall()
            result=migrate_staged_backup(staged,current)
            self.assertEqual(result[0],2)
            with closing(sqlite3.connect(staged)) as connection:
                self.assertEqual(connection.execute('SELECT id,total FROM "transaction" ORDER BY id').fetchall(),before)
                self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0],1)
                self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(),[])
                self.assertEqual(connection.execute('SELECT password_hash FROM user').fetchone()[0],'unchanged-hash')
