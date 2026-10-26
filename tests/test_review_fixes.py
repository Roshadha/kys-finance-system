import secrets
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from tests import test_app as test_support
from app import app, db, Category, Group, Transaction, AuditLog, account_catalog_plan, particular_codes
from backup_settings import read_settings, save_settings

class ReviewFixTests(TestCase):
    setUp = test_support.FinanceAppTests.setUp
    login = test_support.FinanceAppTests.login
    csrf = test_support.FinanceAppTests.csrf

    def test_retry_and_changed_retry_cannot_create_second_entry(self):
        self.login()
        with self.app.app_context():
            cid = Category.query.filter_by(name='Security Service Income').one().id
        data = {'csrf_token':self.csrf(), 'submission_token':secrets.token_hex(16),
                'category_id':cid, 'group_name':'Trade Income', 'year':'2026',
                'month_number':'4', 'subtotal':'100'}
        self.assertEqual(self.client.post('/transactions/new?kind=income',data=data).status_code,302)
        self.assertEqual(self.client.post('/transactions/new?kind=income',data=data).status_code,302)
        data['subtotal']='200'
        self.assertEqual(self.client.post('/transactions/new?kind=income',data=data).status_code,409)
        data.pop('submission_token')
        self.assertEqual(self.client.post('/transactions/new?kind=income',data=data).status_code,400)
        with self.app.app_context():
            self.assertEqual(Transaction.query.count(),1)
            self.assertEqual(Transaction.query.one().total,100)

    def test_reserved_codes_are_excluded_and_custom_accounts_are_retained(self):
        self.login()
        with self.app.app_context():
            group=Group.query.filter_by(name='Trade Income').one()
            item=Category(kind='income',group_id=group.id,group_name=group.name,name='Old hidden',active=False)
            db.session.add(item);db.session.flush()
            db.session.add(AuditLog(action='account_code',entity_type='category',entity_id=item.id,details='900001'))
            db.session.commit()
            expected=max(c for c in particular_codes().values() if c<900000)+100
        self.client.post('/categories',data={'csrf_token':self.csrf(),'kind':'income','group_name':'Trade Income','name':'Custom retained','code':'IP_0'})
        with self.app.app_context():
            custom=Category.query.filter_by(name='Custom retained').one()
            # Calculate income-only expected value independently of the hidden code.
            codes=particular_codes()
            normal=[codes[c.id] for c in Category.query.filter_by(kind='income').all() if c.id!=custom.id and codes[c.id]<900000]
            self.assertEqual(codes[custom.id],max(normal)+100)
            self.assertNotIn(custom,account_catalog_plan()['legacy_particulars'])
            self.assertFalse(account_catalog_plan()['blocked'])
            self.assertIn(custom,account_catalog_plan(retire_unused=True)['legacy_particulars'])

    def test_backup_preferences_are_admin_only_and_persistent(self):
        self.login()
        with tempfile.TemporaryDirectory() as root, patch('app.DATA_ROOT',Path(root)):
            response=self.client.post('/backup/settings',data={'csrf_token':self.csrf(),'interval_minutes':'10'})
            self.assertEqual(response.status_code,302)
            self.assertEqual(read_settings(root)['interval_minutes'],10)
            self.assertEqual(self.client.get('/backup/settings').status_code,200)
            self.client.post('/backup/settings',data={'csrf_token':self.csrf(),'interval_minutes':'0'})
            self.assertEqual(read_settings(root)['interval_minutes'],10)
            self.login('management','Manage@2026')
            self.assertEqual(self.client.get('/backup/settings').status_code,403)
