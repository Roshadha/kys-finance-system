"""Isolated source-level checks; not a substitute for company LAN/PC testing."""
import io
import re
import shutil
import tempfile
import threading
import unittest
import urllib.request
import urllib.parse
import http.cookiejar
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook
from werkzeug.serving import make_server
import app as finance


class HandoverTests(unittest.TestCase):
    def test_concurrent_http_entries_and_backup_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            external = root / 'external-simulation'
            restored = root / 'restored'
            for folder in (source, external, restored):
                folder.mkdir()
            with patch.object(finance, 'DATA_ROOT', source):
                app = finance.create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI':
                    'sqlite:///' + (source / 'data' / 'kys_finance.db').as_posix()})
                with app.app_context():
                    category = finance.Category.query.filter_by(name='Security Service Income').one().id
                server = make_server('127.0.0.1', 0, app, threaded=True)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                barrier = threading.Barrier(4)
                def client(index):
                    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                    base = 'http://127.0.0.1:' + str(server.server_port)
                    def request(path, fields=None):
                        data = urllib.parse.urlencode(fields).encode() if fields else None
                        with opener.open(base + path, data=data, timeout=30) as response:
                            return response.read()
                    page = request('/login').decode()
                    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
                    request('/login', {'username': 'admin', 'password': 'Admin@2026', 'csrf_token': token})
                    page = request('/transactions/new?kind=income').decode()
                    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
                    barrier.wait(timeout=30)
                    for number in range(3):
                        request('/transactions/new?kind=income', {'csrf_token': token, 'kind': 'income',
                            'group_name': 'Trade Income', 'category_id': category, 'cash_date': '2026-10-10',
                            'reference': 'CONCURRENT-{}-{}'.format(index, number), 'subtotal': '100'})
                    return request('/reports?type=monthly&start=2026-10-10&end=2026-10-10')
                try:
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        list(pool.map(client, range(4)))
                    with app.app_context():
                        entries = finance.Transaction.query.all()
                        self.assertEqual(len(entries), 12)
                        self.assertEqual(len({entry.reference for entry in entries}), 12)
                        self.assertEqual(sum(entry.total for entry in entries), 1200)
                    (source / 'backup-target.txt').write_text(str(external), encoding='utf-8')
                    _, backup, error = finance.make_backup(app, force_external=True)
                    self.assertIsNone(error)
                    self.assertTrue((backup / 'backup-complete.txt').exists())
                    (restored / 'data').mkdir()
                    for name in ('kys_finance.db', '.secret_key'):
                        shutil.copy2(backup / name, restored / 'data' / name)
                finally:
                    server.shutdown()
                    thread.join(timeout=10)
                    server.server_close()
                    with app.app_context():
                        finance.db.session.remove()
                        finance.db.engine.dispose()
            with patch.object(finance, 'DATA_ROOT', restored):
                recovered = finance.create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI':
                    'sqlite:///' + (restored / 'data' / 'kys_finance.db').as_posix()})
                try:
                    client = recovered.test_client()
                    client.get('/login')
                    with client.session_transaction() as session:
                        token = session['csrf_token']
                    self.assertEqual(client.post('/login', data={'csrf_token': token,
                        'username': 'admin', 'password': 'Admin@2026'}).status_code, 302)
                    with recovered.app_context():
                        self.assertEqual(finance.Transaction.query.count(), 12)
                        self.assertEqual(sum(t.total for t in finance.Transaction.query.all()), 1200)
                    query = '?type=monthly&start=2026-10-10&end=2026-10-10'
                    self.assertIn(b'1,200.00', client.get('/reports' + query).data)
                    workbook = load_workbook(io.BytesIO(client.get('/reports/export' + query).data))
                    self.assertTrue(any(cell.value == 1200 for sheet in workbook for row in sheet for cell in row))
                    workbook.close()
                finally:
                    with recovered.app_context():
                        finance.db.session.remove()
                        finance.db.engine.dispose()
