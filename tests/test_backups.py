import sqlite3
import tempfile
import unittest
import os
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import app as finance_app


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "server"
        (self.root / "data").mkdir(parents=True)
        self.database = self.root / "data" / "kys_finance.db"
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("CREATE TABLE receipts (amount INTEGER)")
            connection.execute("INSERT INTO receipts VALUES (1250)")
            connection.commit()
        (self.root / "data" / ".secret_key").write_text("test-secret", encoding="utf-8")
        self.app = SimpleNamespace(
            config={"SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database.as_posix()}"},
            logger=Mock(),
        )
        patcher = patch.object(finance_app, "DATA_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_local_and_daily_external_backup(self):
        external = Path(self.temporary.name) / "external"
        external.mkdir()
        (self.root / "backup-target.txt").write_text(str(external), encoding="utf-8")

        local, offsite, error = finance_app.make_backup(self.app)
        self.assertIsNone(error)
        self.assertTrue(local.exists())
        self.assertTrue((offsite / "backup-complete.txt").exists())
        self.assertEqual((offsite / ".secret_key").read_text(encoding="utf-8"), "test-secret")
        with closing(sqlite3.connect(offsite / "kys_finance.db")) as connection:
            self.assertEqual(connection.execute("SELECT amount FROM receipts").fetchone()[0], 1250)

        _, same_day, error = finance_app.make_backup(self.app)
        self.assertIsNone(error)
        self.assertEqual(same_day, offsite)

        _, manual, error = finance_app.make_backup(self.app, force_external=True)
        self.assertIsNone(error)
        self.assertNotEqual(manual, offsite)
        self.assertTrue((manual / "backup-complete.txt").exists())

    def test_external_failure_keeps_local_backup(self):
        (self.root / "backup-target.txt").write_text(str(self.root / "missing-drive"), encoding="utf-8")
        local, offsite, error = finance_app.make_backup(self.app)
        self.assertTrue(local.exists())
        self.assertIsNone(offsite)
        self.assertIn("unavailable", error)

    def test_external_backup_includes_configured_session_secret(self):
        external = Path(self.temporary.name) / "external"
        external.mkdir()
        (self.root / "backup-target.txt").write_text(str(external), encoding="utf-8")
        (self.root / "data" / ".secret_key").unlink()
        with patch.dict(os.environ, {"KYS_SECRET_KEY": "configured-secret"}):
            _, offsite, error = finance_app.make_backup(self.app)
        self.assertIsNone(error)
        self.assertEqual((offsite / ".secret_key").read_text(encoding="utf-8"), "configured-secret")
