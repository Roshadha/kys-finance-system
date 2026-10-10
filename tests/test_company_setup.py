import contextlib
import io
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app as finance


class CompanySetupTests(unittest.TestCase):
    def test_company_bootstrap_requires_private_admin_and_no_demo_accounts(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(finance, 'DATA_ROOT', Path(folder)), patch.dict(os.environ, {'KYS_COMPANY_MODE': '1', 'KYS_DISABLE_BACKUP': '1'}):
            app = finance.create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
            with app.app_context():
                self.assertEqual(finance.User.query.count(), 0)
            script = str(Path(__file__).resolve().parents[1] / 'legacy' / 'server_company.py')
            with patch.object(finance, 'app', app), patch('sys.argv', [script, '--configure-admin']), patch('builtins.input', return_value='company-owner'), patch('getpass.getpass', side_effect=['TemporaryOnly!234', 'TemporaryOnly!234']), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    runpy.run_path(script, run_name='__main__')
                self.assertEqual(result.exception.code, 0)
            with app.app_context():
                self.assertEqual(finance.User.query.count(), 1)
                self.assertEqual(finance.User.query.one().username, 'company-owner')
                self.assertNotEqual(finance.User.query.one().password_hash, 'TemporaryOnly!234')
            client = app.test_client()
            self.assertEqual(client.get('/reports').status_code, 302)
            client.get('/login')
            with client.session_transaction() as session:
                token = session['csrf_token']
            self.assertEqual(client.post('/login', data={'csrf_token': token, 'username': 'admin', 'password': 'Admin@2026'}).status_code, 200)
            self.assertEqual(client.post('/login', data={'csrf_token': token, 'username': 'company-owner', 'password': 'TemporaryOnly!234'}).status_code, 302)
            with app.app_context():
                finance.db.session.remove()
                finance.db.engine.dispose()
