import os
import unittest
from datetime import date
from unittest.mock import patch
from html import unescape
import re
from werkzeug.security import check_password_hash

os.environ["KYS_DISABLE_BACKUP"] = "1"

from app import Adjustment, Category, Transaction, User, Group, AuditLog, build_report, group_codes, particular_codes, sorted_groups, sorted_categories, seed_database, create_app, db


class FinanceAppTests(unittest.TestCase):
    def test_closed_month_blocks_edit_delete_and_reopen_restores_access(self):
        self.login()
        with self.app.app_context():
            item = Transaction(cash_date=date(2026, 1, 1), category_id=Category.query.first().id,
                created_by_id=User.query.filter_by(username='admin').one().id,
                reference='lock', counterparty='', subtotal=100, total=100)
            db.session.add(item)
            db.session.commit()
            identifier = item.id
        fields = {'csrf_token': self.csrf(), 'year': '2026', 'month_number': '1', 'action': 'close', 'reason': 'Month approved'}
        self.assertEqual(self.client.post('/reports/period-status', data=fields).status_code, 302)
        for suffix in ('edit', 'delete', 'adjust'):
            self.assertEqual(self.client.post('/transactions/{}/{}'.format(identifier, suffix), data={'csrf_token': self.csrf(), 'confirmed': 'yes'}).status_code, 409)
        fields['action'] = 'open'
        fields['reason'] = 'Approved correction'
        self.assertEqual(self.client.post('/reports/period-status', data=fields).status_code, 302)
        self.assertEqual(self.client.post('/transactions/{}/delete'.format(identifier), data={'csrf_token': self.csrf(), 'confirmed': 'yes'}).status_code, 302)

    def test_login_throttle_and_old_sessions_revoked(self):
        self.client.get('/login')
        for _ in range(10):
            self.client.post('/login', data={'csrf_token': self.csrf(), 'username': 'missing', 'password': 'wrong'})
        self.assertEqual(self.client.post('/login', data={'csrf_token': self.csrf()}).status_code, 429)
        with self.client.session_transaction() as state:
            state['user_id'] = 1
            state.pop('auth_stamp', None)
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_decimal_input_rounding_and_invalid_values(self):
        from app import parse_money
        from decimal import Decimal
        self.assertEqual(parse_money('2.675'), Decimal('2.68'))
        for value in ('NaN', 'Infinity', '999999999999.999'):
            with self.assertRaises(ValueError):
                parse_money(value)

    def test_used_particular_cannot_reclassify_historic_entries(self):
        self.login()
        with self.app.app_context():
            category = Category.query.filter_by(kind='income').first()
            expense = Group.query.filter_by(kind='expense').first()
            identifier, group_id = category.id, expense.id
            db.session.add(Transaction(cash_date=date(2026, 1, 1), category_id=identifier,
                created_by_id=User.query.filter_by(username='admin').one().id,
                reference='guard', counterparty='', subtotal=100, total=100))
            db.session.commit()
        response = self.client.post('/categories/' + identifier + '/edit', data={
            'csrf_token': self.csrf(), 'kind': 'expense', 'group_id': group_id,
            'name': 'Reclassified', 'code': 'EP_9900'})
        self.assertIn(b'posted entries', response.data)
        with self.app.app_context():
            self.assertEqual(db.session.get(Category, identifier).kind, 'income')

    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        self.client = self.app.test_client()

    def csrf(self):
        with self.client.session_transaction() as sess:
            return sess["csrf_token"]

    def login(self, username="admin", password="Admin@2026"):
        self.client.get("/login")
        return self.client.post("/login", data={
            "csrf_token": self.csrf(), "username": username, "password": password,
        })

    def test_role_access_and_health(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.login("management", "Manage@2026").status_code, 302)
        self.assertEqual(self.client.get("/reports").status_code, 200)
        self.assertEqual(self.client.get("/users").status_code, 403)

    def test_only_admin_sees_or_uses_change_password(self):
        self.login("management", "Manage@2026")
        with self.app.app_context():
            original_hash = User.query.filter_by(username="management").one().password_hash
        self.assertNotIn(b'title="Change password"', self.client.get("/").data)
        self.assertEqual(self.client.get("/account/password").status_code, 403)
        self.assertEqual(self.client.post("/account/password", data={
            "csrf_token": self.csrf(), "current_password": "Manage@2026",
            "new_password": "NewSecret123",
        }).status_code, 403)
        with self.app.app_context():
            self.assertEqual(User.query.filter_by(username="management").one().password_hash, original_hash)

    def test_report_month_range_and_single_month_override(self):
        self.login()
        with self.app.app_context():
            category = Category.query.filter_by(kind='income').first()
            admin = User.query.filter_by(username='admin').one()
            for month, amount in [(5, 10), (6, 100), (9, 200), (10, 1000)]:
                db.session.add(Transaction(category_id=category.id, created_by_id=admin.id,
                    cash_date=date(2026, month, 15), reference='RANGE', counterparty='',
                    subtotal=amount, total=amount, sscl=0, vat=0))
            db.session.commit()
        query = 'from_year=2026&from_month=6&to_year=2026&to_month=9'
        self.assertIn(b'Rs. 300.00', self.client.get('/reports?' + query).data)
        self.assertIn(b'Rs. 100.00', self.client.get('/reports?' + query + '&period_mode=one').data)
        self.assertIn(b'Rs. 300.00', self.client.get('/reports?from_year=2026&from_month=9&to_year=2026&to_month=6').data)
        self.assertEqual(self.client.get('/reports/export?' + query).status_code, 200)
        self.assertEqual(self.client.get('/reports?from_year=2026&from_month=13').status_code, 400)

    def test_live_updates_across_users_and_entry_changes(self):
        self.assertEqual(self.client.get('/updates/version').status_code, 401)
        self.login()
        reader = self.app.test_client()
        reader.get('/login')
        with reader.session_transaction() as state:
            token = state['csrf_token']
        reader.post('/login', data={'csrf_token': token, 'username': 'management', 'password': 'Manage@2026'})
        before = reader.get('/updates/version')
        self.assertEqual(before.headers['Cache-Control'], 'no-store')
        version = before.json['version']
        self.client.get('/reports/export')
        self.assertEqual(reader.get('/updates/version').json['version'], version)
        with self.app.app_context():
            category = Category.query.filter_by(name='Security Service Income').one()
            category_id, group_name = category.id, category.group_name
        result = self.client.post('/transactions/new?kind=income', data={
            'csrf_token': self.csrf(), 'category_id': category_id, 'group_name': group_name,
            'month_number': '10', 'year': '2026', 'subtotal': '125', 'reference': 'LIVE-TEST'})
        self.assertEqual(result.status_code, 302)
        changed = reader.get('/updates/version').json['version']
        self.assertNotEqual(changed, version)
        for path in ['/?month=2026-10', '/transactions?year=2026&month_number=10', '/reports?year=2026&month_number=10']:
            page = reader.get(path)
            self.assertIn(b'id="liveUpdates"', page.data)
            self.assertIn(changed.encode(), page.data)
            self.assertIn(b'125.00', page.data)
        self.assertNotIn(b'id="liveUpdates"', self.client.get('/transactions/new?kind=income').data)
        with self.app.app_context():
            transaction_id = Transaction.query.filter_by(reference='LIVE-TEST').one().id
        self.client.post(f'/transactions/{transaction_id}/edit', data={
            'csrf_token': self.csrf(), 'version': '0', 'total': '150', 'reason': 'Live edit'})
        edited = reader.get('/updates/version').json['version']
        self.assertNotEqual(edited, changed)
        self.client.post(f'/transactions/{transaction_id}/delete', data={'csrf_token': self.csrf(), 'confirmed': 'yes'})
        self.assertNotEqual(reader.get('/updates/version').json['version'], edited)
        with self.app.app_context():
            User.query.filter_by(username='management').one().active = False
            db.session.commit()
        self.assertEqual(reader.get('/updates/version').status_code, 401)

    def test_dashboard_month_links_follow_calendar_boundaries(self):
        class MarchFirst(date):
            @classmethod
            def today(cls):
                return cls(2024, 3, 1)

        self.login("recovery", "KysRec@2026")
        self.assertEqual(self.client.get('/').status_code, 302)
        self.login('management', 'Manage@2026')
        with patch("app.date", MarchFirst):
            page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        links = re.findall(r'class="bar-group month-link" href="([^"]+)"', page.get_data(as_text=True))
        self.assertEqual([unescape(link) for link in links], [
            "/?month=2023-10", "/?month=2023-11", "/?month=2023-12",
            "/?month=2024-01", "/?month=2024-02", "/?month=2024-03",
        ])
        self.assertIn(b'View February 2024 overview', page.data)
        empty = self.client.get(unescape(links[4]))
        self.assertEqual(empty.status_code, 200)
        self.assertIn(b'No entries in this period', empty.data)

    def test_month_drilldown_includes_only_selected_month(self):
        self.login()
        with self.app.app_context():
            income = Category.query.filter_by(kind="income", name="Security Service Income").first()
            expense = Category.query.filter_by(kind="expense", name="Office Expenditure").first()
            admin = User.query.filter_by(username="admin").one()
            for day, ref, category in [
                (date(2024, 1, 31), "BEFORE-MONTH", income),
                (date(2024, 2, 1), "FIRST-DAY-INCOME", income),
                (date(2024, 2, 29), "LAST-DAY-EXPENSE", expense),
                (date(2024, 3, 1), "AFTER-MONTH", expense),
            ]:
                db.session.add(Transaction(category_id=category.id, cash_date=day,
                    reference=ref, counterparty="Test", subtotal=100 if category.kind == 'income' else 30,
                    sscl=0, vat=0, total=100 if category.kind == 'income' else 30, created_by_id=admin.id))
            db.session.commit()
        page = self.client.get("/?month=2024-02")
        self.assertEqual(page.status_code, 200)
        for text in (b'FIRST-DAY-INCOME', b'LAST-DAY-EXPENSE', b'01 Feb 2024', b'29 Feb 2024'):
            self.assertIn(text, page.data)
        for text in (b'BEFORE-MONTH', b'AFTER-MONTH'):
            self.assertNotIn(text, page.data)
        for text in (b'Rs. 100.00', b'Rs. 30.00', b'Rs. 70.00', b'Cash entries for February 2024'):
            self.assertIn(text, page.data)
        self.assertIn(b'/transactions?start=2024-02-01&amp;end=2024-02-29', page.data)
        self.assertIn(b'29 Feb 2024</p>', page.data)
        self.assertEqual(self.client.get('/?month=invalid').status_code, 400)

    def test_admin_can_manage_accounts_and_user_assignments(self):
        self.login()
        self.assertEqual(self.client.get("/categories").status_code, 200)
        self.assertEqual(self.client.get("/users/3/edit").status_code, 200)
        response = self.client.post("/users/3/edit", data={
            "csrf_token": self.csrf(), "display_name": "Recovery Department",
            "department": "Recovery", "role": "data_entry",
            "tasks": ["income_entry", "vat_entry", "view_reports"], "password": "",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertIn("view_reports", User.query.filter_by(username="recovery").one().tasks)

    def test_admin_can_edit_every_account_field_and_delete_without_losing_history(self):
        self.login()
        with self.app.app_context():
            staff = User.query.filter_by(username='recovery').one()
            admin = User.query.filter_by(username='admin').one()
            category = Category.query.filter_by(name='Security Service Income').one()
            staff_id = staff.id
            admin_id = admin.id
            db.session.add(Transaction(category_id=category.id, cash_date=date(2024, 1, 1),
                reference='STAFF-HISTORY', counterparty='', subtotal=10, sscl=0, vat=0,
                total=10, created_by_id=staff_id))
            db.session.commit()
        edit_page = self.client.get(f'/users/{staff_id}/edit')
        self.assertIn(b'name="username"', edit_page.data)
        self.assertIn(b'name="active"', edit_page.data)
        response = self.client.post(f'/users/{staff_id}/edit', data={
            'csrf_token': self.csrf(), 'username': 'accounts', 'display_name': 'Accounts Team',
            'department': 'Finance', 'role': 'management', 'active': 'yes',
            'tasks': ['view_reports'], 'password': 'New456',
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            staff = db.session.get(User, staff_id)
            self.assertEqual((staff.username, staff.display_name, staff.department, staff.role),
                             ('accounts', 'Accounts Team', 'Finance', 'management'))
            self.assertEqual(staff.tasks, ['view_reports'])
            self.assertTrue(check_password_hash(staff.password_hash, 'New456'))
            self.assertEqual(Transaction.query.filter_by(reference='STAFF-HISTORY').one().created_by_id, staff_id)
        other = self.app.test_client()
        other.get('/login')
        with other.session_transaction() as state:
            token = state['csrf_token']
        self.assertIn(b'incorrect', other.post('/login', data={
            'csrf_token': token, 'username': 'recovery', 'password': 'KysRec@2026',
        }).data)
        self.assertEqual(other.post('/login', data={
            'csrf_token': token, 'username': 'accounts', 'password': 'New456',
        }).status_code, 302)
        self.assertEqual(self.client.post(f'/users/{admin_id}/delete', data={
            'csrf_token': self.csrf(), 'confirmed': 'yes',
        }).status_code, 302)
        self.assertEqual(self.client.get('/users').status_code, 200)
        self.assertEqual(self.client.get(f'/users/{staff_id}/delete').status_code, 200)
        self.assertEqual(self.client.post(f'/users/{staff_id}/delete', data={
            'csrf_token': self.csrf(), 'confirmed': 'yes',
        }).status_code, 302)
        self.assertEqual(self.client.get(f'/users/{staff_id}/edit').status_code, 404)
        self.assertNotIn(b'Accounts Team', self.client.get('/users').data)
        self.assertEqual(other.get('/reports').status_code, 302)
        with self.app.app_context():
            staff = db.session.get(User, staff_id)
            self.assertTrue(staff.deleted)
            self.assertFalse(staff.active)
            self.assertEqual(Transaction.query.filter_by(reference='STAFF-HISTORY').one().created_by.username, 'accounts')
            self.assertIsNotNone(AuditLog.query.filter_by(action='delete', entity_type='user', entity_id=str(staff_id)).first())

    def test_user_edit_rejects_duplicate_username_and_self_lockout(self):
        self.login()
        with self.app.app_context():
            admin_id = User.query.filter_by(username='admin').one().id
            staff_id = User.query.filter_by(username='recovery').one().id
        response = self.client.post(f'/users/{staff_id}/edit', data={
            'csrf_token': self.csrf(), 'username': 'MANAGEMENT', 'display_name': 'Recovery',
            'role': 'data_entry', 'active': 'yes',
        })
        self.assertIn(b'already in use', response.data)
        response = self.client.post(f'/users/{admin_id}/edit', data={
            'csrf_token': self.csrf(), 'username': 'admin', 'display_name': 'Admin',
            'role': 'management', 'active': 'no',
        })
        self.assertIn(b'cannot disable', response.data)
        with self.app.app_context():
            admin = db.session.get(User, admin_id)
            self.assertTrue(admin.active)
            self.assertEqual(admin.role, 'admin')

    def test_month_entry_remembered_and_expense_tax_rejected(self):
        self.login()
        with self.app.app_context():
            cat = Category.query.filter_by(name='Office Expenditure').one()
            cid, group = cat.id, cat.group_name
        fields = dict(csrf_token=self.csrf(), kind='expense', category_id=cid,
                      group_name=group, month_number='2', year='2024', subtotal='8000')
        response = self.client.post('/transactions/new?kind=expense', data=fields, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(Transaction.query.one().cash_date, date(2024, 2, 1))
        self.assertIn(b'value="2" selected', response.data)
        self.assertIn(b'value="2024" selected', response.data)
        self.assertNotIn(b'id="sscl"', response.data)
        fields['vat'] = '10'
        self.client.post('/transactions/new?kind=expense', data=fields)
        with self.app.app_context():
            self.assertEqual(Transaction.query.count(), 1)

    def test_selected_entry_month_persists_without_posting_and_across_login(self):
        self.login()
        fields = dict(csrf_token=self.csrf(), month_number='2', year='2024')
        self.assertEqual(self.client.post('/account/entry-period', data=fields).status_code, 200)
        self.assertEqual(self.client.post('/account/entry-period', data=fields).status_code, 200)
        with self.app.app_context():
            self.assertEqual(Transaction.query.count(), 0)
            self.assertEqual(AuditLog.query.filter_by(action='entry_period').count(), 1)
        self.client.post('/logout', data={'csrf_token': self.csrf()})
        self.login()
        for kind in ('income', 'expense'):
            page = self.client.get('/transactions/new?kind=' + kind)
            self.assertIn(b'value="2" selected', page.data)
            self.assertIn(b'value="2024" selected', page.data)
        self.assertNotIn(b'View month', self.client.get('/').data)
        fields['csrf_token'] = self.csrf()
        fields['month_number'] = '13'
        self.assertEqual(self.client.post('/account/entry-period', data=fields).status_code, 400)
        self.assertEqual(self.client.post('/account/entry-period', data={'month_number':'3','year':'2024'}).status_code,400)
        self.login('recovery', 'KysRec@2026')
        self.client.post('/account/entry-period',data={'csrf_token':self.csrf(), 'month_number':'7', 'year':'2025'})
        self.login()
        self.assertIn(b'value="2024" selected', self.client.get('/transactions/new?kind=income').data)
        self.client.post('/account/entry-period',data={'csrf_token':self.csrf(), 'month_number':'6', 'year':'2023'})
        self.assertIn(b'value="6" selected', self.client.get('/transactions/new?kind=expense').data)
        self.login('management', 'Manage@2026')
        self.assertEqual(self.client.post('/account/entry-period',data={'csrf_token':self.csrf(), 'month_number':'6','year':'2023'}).status_code,403)

    def test_admin_public_codes_sorting_and_removed_fields(self):
        self.login()
        self.assertEqual(self.client.get('/vehicles').status_code, 404)
        for kind in ('income', 'expense'):
            page = self.client.get('/transactions/new?kind=' + kind)
            for field in (b'id="sscl"', b'id="vat"', b'name="vehicle_id"'):
                self.assertNotIn(field, page.data)
        with self.app.app_context():
            self.assertEqual(group_codes()['IG_100'], 10)
            cat = Category.query.filter_by(name='Office Expenditure').one()
            cid, gid, group = cat.id, cat.group_id, cat.group_name
            self.assertEqual(particular_codes()['EP_0010'], 100)
            self.assertEqual(particular_codes()['EP_0020'], 200)
        self.client.post('/categories', data={'csrf_token':self.csrf(), 'kind':'expense',
            'group_name':group, 'name':'Custom coded account', 'code':'EP_0099'})
        with self.app.app_context():
            new = Category.query.filter_by(name='Custom coded account').one()
            new_id = new.id
            self.assertEqual(particular_codes()[new_id],99)
            ordered = sorted_categories(Category.query.filter_by(group_id=gid).all())
            self.assertEqual(ordered[0].id,new_id)
        self.client.post(f'/categories/{new_id}/edit', data={'csrf_token':self.csrf(),'code':'EP_0100'})
        with self.app.app_context():
            self.assertEqual(particular_codes()[new_id],99)  # Duplicate rejected.
        self.client.post(f'/categories/{new_id}/edit', data={'csrf_token':self.csrf(),'code':'EP_0050'})
        with self.app.app_context():
            self.assertEqual(particular_codes()[new_id],50)
        self.login('management','Manage@2026')
        self.assertEqual(self.client.post(f'/categories/{cid}/edit',data={'csrf_token':self.csrf(),'code':'10'}).status_code,403)
        self.assertEqual(self.client.post(f'/groups/{gid}/edit',data={'csrf_token':self.csrf(),'name':group,'code':'10'}).status_code,403)

    def test_admin_can_edit_all_particular_fields_and_actions_are_separate(self):
        self.login()
        with self.app.app_context():
            item = Category.query.filter_by(name='Office Expenditure').one()
            item_id = item.id
            other_group = Group.query.filter(Group.kind == 'expense', Group.id != item.group_id).first()
            self.assertIsNotNone(other_group)
            group_id = other_group.id
        listing = self.client.get('/categories').data
        self.assertIn(b'class="account-action"', listing)
        self.assertIn(b'class="account-action account-action-hide"', listing)
        groups_listing = self.client.get('/groups').data
        self.assertIn(b'class="account-actions"', groups_listing)
        self.assertIn(b'class="account-action account-action-hide"', groups_listing)
        with self.app.app_context():
            hidden_category = Category.query.filter_by(name='Bank Interest Received').one()
            hidden_group = Group.query.filter_by(kind='income', name='Bank Interest Income').one()
            hidden_category_id, hidden_group_id = hidden_category.id, hidden_group.id
        self.client.post(f'/categories/{hidden_category_id}/toggle', data={'csrf_token': self.csrf()})
        self.client.post(f'/groups/{hidden_group_id}/toggle', data={'csrf_token': self.csrf()})
        self.assertIn(b'class="account-action account-action-enable"', self.client.get('/categories').data)
        self.assertIn(b'class="account-action account-action-enable"', self.client.get('/groups').data)
        edit_page = self.client.get(f'/categories/{item_id}/edit').data
        for field in (b'name="kind"', b'name="group_id"', b'name="code"',
                      b'name="name"', b'name="service_line"', b'name="entity_name"'):
            self.assertIn(field, edit_page)
        response = self.client.post(f'/categories/{item_id}/edit', data={
            'csrf_token': self.csrf(), 'kind': 'expense', 'group_id': group_id,
            'code': 'EP_9999', 'name': 'Updated Office Expenditure',
            'service_line': 'Cleaning', 'entity_name': 'Project A',
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            item = db.session.get(Category, item_id)
            self.assertEqual((item.group_id, item.group_name, item.name),
                             (group_id, other_group.name, 'Updated Office Expenditure'))
            self.assertEqual((item.service_line, item.entity_name), ('Cleaning', 'Project A'))
            self.assertEqual(particular_codes()[item_id], 9999)
            self.assertIsNotNone(AuditLog.query.filter_by(action='edit', entity_type='category', entity_id=item_id).first())
        invalid = self.client.post(f'/categories/{item_id}/edit', data={
            'csrf_token': self.csrf(), 'kind': 'income', 'group_id': group_id,
            'code': 'IP_9998', 'name': 'Wrong group',
        })
        self.assertEqual(invalid.status_code, 200)
        with self.app.app_context():
            self.assertEqual(db.session.get(Category, item_id).name, 'Updated Office Expenditure')

    def test_six_character_passwords_are_accepted_but_five_are_not(self):
        self.login()
        self.assertIn(b'minlength="6"', self.client.get('/users/new').data)
        self.client.post('/users/new', data={
            'csrf_token': self.csrf(), 'username': 'sixuser', 'display_name': 'Six User',
            'department': 'Accounts', 'role': 'data_entry', 'password': 'Abc123',
        })
        self.client.post('/users/new', data={
            'csrf_token': self.csrf(), 'username': 'fiveuser', 'display_name': 'Five User',
            'department': 'Accounts', 'role': 'data_entry', 'password': 'Ab123',
        })
        with self.app.app_context():
            six = User.query.filter_by(username='sixuser').one()
            self.assertTrue(check_password_hash(six.password_hash, 'Abc123'))
            self.assertIsNone(User.query.filter_by(username='fiveuser').first())
            six_id = six.id
        self.client.post(f'/users/{six_id}/edit', data={
            'csrf_token': self.csrf(), 'display_name': 'Six User', 'role': 'data_entry',
            'password': 'New456',
        })
        with self.app.app_context():
            self.assertTrue(check_password_hash(db.session.get(User, six_id).password_hash, 'New456'))
        self.assertIn(b'minlength="6"', self.client.get('/account/password').data)
        self.client.post('/account/password', data={
            'csrf_token': self.csrf(), 'current_password': 'Admin@2026',
            'new_password': 'Adm123',
        })
        with self.app.app_context():
            admin = User.query.filter_by(username='admin').one()
            self.assertTrue(check_password_hash(admin.password_hash, 'Adm123'))

    def test_delete_excludes_entry_adjustments_and_retains_audit(self):
        self.login()
        with self.app.app_context():
            cat = Category.query.filter_by(name='Security Service Income').one()
            admin = User.query.filter_by(username='admin').one()
            txn = Transaction(category_id=cat.id, cash_date=date(2024, 2, 1), reference='VOID-ME',
                              counterparty='', subtotal=100, sscl=0, vat=0, total=100, created_by_id=admin.id)
            db.session.add(txn)
            db.session.flush()
            tid = txn.id
            db.session.add(Adjustment(transaction_id=tid, effective_date=date(2024, 2, 2), amount=20, reason='test', created_by_id=admin.id))
            db.session.commit()
        path = f'/transactions/{tid}/delete'
        self.client.post(path, data={'csrf_token': self.csrf(), 'reason': ''})
        with self.app.app_context():
            self.assertEqual(build_report(date(2024,2,1), date(2024,2,29))['income'], 120)
        page = self.client.get(path)
        self.assertNotIn(b'name="reason"', page.data)
        self.assertIn(b'name="confirmed" value="yes"', page.data)
        self.client.post(path, data={'csrf_token': self.csrf(), 'confirmed': 'yes'})
        with self.app.app_context():
            self.assertEqual(Transaction.query.count(), 1)
            self.assertEqual(Adjustment.query.count(), 1)
            self.assertEqual(AuditLog.query.filter_by(action='delete').count(), 1)
            self.assertEqual(build_report(date(2024,2,1), date(2024,2,29))['income'], 0)
        self.assertNotIn(b'VOID-ME', self.client.get('/?month=2024-02').data)
        self.assertNotIn(b'VOID-ME', self.client.get('/transactions?year=2024&month_number=2').data)
        self.assertEqual(self.client.get(f'/transactions/{tid}/adjust').status_code, 404)
        self.login('recovery', 'KysRec@2026')
        self.assertEqual(self.client.post(path, data={'csrf_token': self.csrf(), 'reason': 'x'}).status_code, 403)

    def test_group_code_rename_hide_and_tax_identity(self):
        self.login()
        with self.app.app_context():
            tax = Category.query.filter_by(kind='income', name='SSCL').one()
            self.assertEqual(tax.id, 'IP_0190')
            self.assertEqual(Category.query.filter_by(kind='income', name='VAT').one().id, 'IP_0200')
            gid, cid = tax.group_id, tax.id
        self.client.post(f'/groups/{gid}/edit', data={'csrf_token':self.csrf(), 'name':'Taxes received', 'code':'50'})
        with self.app.app_context():
            self.assertEqual(group_codes()[gid], 50)
            self.assertEqual(db.session.get(Category,cid).group_name, 'Taxes received')
            seed_database()
            self.assertEqual(Category.query.filter_by(kind='income',name='SSCL').count(),1)
        self.client.post(f'/groups/{gid}/toggle', data={'csrf_token':self.csrf()})
        self.assertNotIn(cid.encode(), self.client.get('/transactions/new?kind=income').data)
        self.client.post('/transactions/new?kind=income', data={'csrf_token':self.csrf(), 'category_id':cid,
            'group_name':'Taxes received','year':'2024','month_number':'2','subtotal':'100'})
        with self.app.app_context():
            self.assertEqual(Transaction.query.count(),0)

    def test_group_type_code_prefix_uniqueness_and_numeric_order(self):
        self.login()
        page = self.client.get('/groups').data
        self.assertIn(b'id="groupCreateForm"', page)
        self.assertIn(b'value="IG_0"', page)
        self.assertIn(b'id="groupEditForm"', self.client.get('/groups/IG_100/edit').data)
        self.assertIn(b'name="kind"', self.client.get('/groups/IG_100/edit').data)

        self.client.post('/groups', data={'csrf_token': self.csrf(), 'kind': 'income',
            'name': 'Between group codes', 'code': 'IG_0011'})
        with self.app.app_context():
            added = Group.query.filter_by(name='Between group codes').one()
            added_id = added.id
            self.assertEqual(group_codes()[added_id], 11)
            ordered = [group_codes()[group.id] for group in sorted_groups(Group.query.filter_by(kind='income').all())]
            self.assertLess(ordered.index(10), ordered.index(11))
            self.assertLess(ordered.index(11), ordered.index(20))
        self.client.post('/groups', data={'csrf_token': self.csrf(), 'kind': 'income',
            'name': 'Duplicate code', 'code': 'IG_0011'})
        with self.app.app_context():
            self.assertIsNone(Group.query.filter_by(name='Duplicate code').first())
        self.client.post(f'/groups/{added_id}/toggle', data={'csrf_token': self.csrf()})
        self.client.post('/groups', data={'csrf_token': self.csrf(), 'kind': 'income',
            'name': 'Hidden duplicate code', 'code': 'IG_0011'})
        with self.app.app_context():
            self.assertIsNone(Group.query.filter_by(name='Hidden duplicate code').first())

        self.client.post('/groups', data={'csrf_token': self.csrf(), 'kind': 'income',
            'name': 'Automatic prefix group', 'code': 'IG_0'})
        with self.app.app_context():
            automatic = Group.query.filter_by(name='Automatic prefix group').one()
            automatic_id = automatic.id
            self.assertEqual(group_codes()[automatic_id], 60)
        response = self.client.post(f'/groups/{automatic_id}/edit', data={
            'csrf_token': self.csrf(), 'kind': 'expense', 'name': 'Moved empty group',
            'code': 'EG_0071'})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            moved = db.session.get(Group, automatic_id)
            self.assertEqual((moved.kind, moved.name, group_codes()[automatic_id]),
                             ('expense', 'Moved empty group', 71))
        response = self.client.post('/groups/IG_100/edit', data={
            'csrf_token': self.csrf(), 'kind': 'expense', 'name': 'Trade Income',
            'code': 'EG_0072'}, follow_redirects=True)
        self.assertIn(b'Move this group', response.data)
        with self.app.app_context():
            self.assertEqual(db.session.get(Group, 'IG_100').kind, 'income')

    def test_particular_code_prefix_auto_assigns_next_for_each_type(self):
        self.login()
        page = self.client.get('/categories').data
        self.assertIn(b'id="categoryCreateForm"', page)
        self.assertIn(b'value="IP_0"', page)
        with self.app.app_context():
            previous = {
                kind: max(particular_codes()[item.id] for item in Category.query.filter_by(kind=kind).all())
                for kind in ('income', 'expense')
            }
        for kind, group_name, prefix in (
            ('income', 'Trade Income', 'IP'),
            ('expense', 'Operational Expenditure', 'EP'),
        ):
            response = self.client.post('/categories', data={
                'csrf_token': self.csrf(), 'kind': kind, 'group_name': group_name,
                'code': prefix + '_0', 'name': 'Automatic ' + kind + ' code',
            })
            self.assertEqual(response.status_code, 302)
            with self.app.app_context():
                item = Category.query.filter_by(name='Automatic ' + kind + ' code').one()
                self.assertEqual(particular_codes()[item.id], previous[kind] + 100)

    def test_edit_absolute_total_with_history_and_stale_form_protection(self):
        self.login()
        with self.app.app_context():
            cat = Category.query.filter_by(name='Security Service Income').one()
            admin = User.query.filter_by(username='admin').one()
            txn = Transaction(category_id=cat.id, cash_date=date(2024, 2, 1), reference='EDIT-ME',
                counterparty='', subtotal=12000, sscl=0, vat=0, total=12000, created_by_id=admin.id)
            db.session.add(txn)
            db.session.commit()
            tid = txn.id
        path = f'/transactions/{tid}/edit'
        page = self.client.get(path)
        self.assertIn(b'value="12,000.00"', page.data)
        self.assertIn(b'Save changes', page.data)
        fields = dict(csrf_token=self.csrf(), version='0', total='10,000.00', reason='Correct amount')
        result = self.client.post(path, data=fields)
        self.assertEqual(result.status_code, 302)
        self.assertIn('month_number=2', result.location)
        with self.app.app_context():
            txn = db.session.get(Transaction, tid)
            self.assertEqual(txn.total, 12000)
            self.assertEqual(txn.adjusted_total, 10000)
            self.assertEqual(Adjustment.query.one().amount, -2000)
            self.assertEqual(AuditLog.query.filter_by(action='edit').count(), 1)
            self.assertEqual(build_report(date(2024,2,1), date(2024,2,29))['income'], 10000)
            version = str(Adjustment.query.one().id)
        # Repeated submit and another stale browser tab cannot apply the edit twice.
        self.assertIn(b'changed since you opened', self.client.post(path, data=fields).data)
        fields.update(version=version, total='13,500.25')
        self.assertEqual(self.client.post(path, data=fields).status_code, 302)
        with self.app.app_context():
            self.assertEqual(db.session.get(Transaction, tid).adjusted_total, 13500.25)
            fields['version'] = str(Adjustment.query.order_by(Adjustment.id.desc()).first().id)
        self.client.post(path, data=fields)  # Same amount is a no-op.
        for invalid in ('', '-1', '0', 'NaN', 'Infinity', 'abc'):
            fields['total'] = invalid
            self.assertEqual(self.client.post(path, data=fields).status_code, 200)
        fields.update(total='14000', reason='')
        self.client.post(path, data=fields)
        with self.app.app_context():
            self.assertEqual(Adjustment.query.count(), 2)
            self.assertEqual(db.session.get(Transaction, tid).adjusted_total, 13500.25)
        self.assertEqual(self.client.post(path, data={'total': '1'}).status_code, 400)
        for user, password in [('management', 'Manage@2026'), ('recovery', 'KysRec@2026')]:
            self.login(user, password)
            self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(self.client.post(path, data=dict(fields, csrf_token=self.csrf())).status_code, 403)
        self.login()
        self.client.post(f'/transactions/{tid}/delete', data={'csrf_token':self.csrf(), 'confirmed':'yes'})
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(path, data=dict(fields, csrf_token=self.csrf())).status_code, 404)

    def test_locked_transaction_adjustment_and_excel_export(self):
        self.login()
        with self.app.app_context():
            category_id = Category.query.filter_by(kind="income", name="Security Service Income").first().id
        response = self.client.post("/transactions/new?kind=income", data={
            "csrf_token": self.csrf(), "kind": "income", "group_name": "Trade Income", "category_id": category_id,
            "cash_date": date.today().isoformat(), "reference": "TEST-001",
            "counterparty": "Test Customer", "description": "Cash receipt",
            "subtotal": "100000",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            txn = Transaction.query.filter_by(reference="TEST-001").one()
            self.assertEqual(float(txn.total), 100000)
            txn_id = txn.id
        response = self.client.post(f"/transactions/{txn_id}/adjust", data={
            "csrf_token": self.csrf(), "effective_date": date.today().isoformat(),
            "amount": "-5000", "reason": "Invoice value correction",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(Adjustment.query.filter_by(transaction_id=txn_id).count(), 1)
            self.assertEqual(db.session.get(Transaction, txn_id).adjusted_total, 95000)
        export = self.client.get(f"/reports/export?type=monthly&start={date.today()}&end={date.today()}")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.data[:2], b"PK")

    def test_data_entry_task_restrictions(self):
        self.login("recovery", "KysRec@2026")
        self.assertEqual(self.client.get("/transactions/new?kind=income").status_code, 200)
        self.assertEqual(self.client.get("/transactions/new?kind=expense").status_code, 403)
        self.assertEqual(self.client.get("/reports").status_code, 403)

    def test_group_account_selection_and_optional_reference_counterparty(self):
        self.login()
        with self.app.app_context():
            income = Category.query.filter_by(kind="income", name="Security Service Income").first()
            expense = Category.query.filter_by(kind="expense", name="Office Expenditure").first()
            account_ids = (("income", income.group_name, income.id),
                           ("expense", expense.group_name, expense.id))
        for kind, group, account_id in account_ids:
            page = self.client.get(f"/transactions/new?kind={kind}")
            self.assertIn(b'transactionGroupSelect', page.data)
            self.assertIn(b'data-group=', page.data)
            response = self.client.post(f"/transactions/new?kind={kind}", data={
                "csrf_token": self.csrf(), "kind": kind, "group_name": group,
                "category_id": account_id, "cash_date": date.today().isoformat(),
                "reference": "", "counterparty": "", "subtotal": "125.00",
            })
            self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(Transaction.query.filter_by(reference="", counterparty="").count(), 2)
        mismatch = self.client.post("/transactions/new?kind=income", data={
            "csrf_token": self.csrf(), "kind": "income", "group_name": "Rental Income",
            "category_id": account_ids[0][2], "cash_date": date.today().isoformat(),
            "subtotal": "125.00",
        })
        self.assertEqual(mismatch.status_code, 200)
        self.assertIn(b'Select a valid account.', mismatch.data)

    def test_grouped_money_input_is_saved_at_its_numeric_value(self):
        self.login()
        with self.app.app_context():
            category = Category.query.filter_by(kind="expense", name="Office Expenditure").first()
            category_id, group_name = category.id, category.group_name
        page = self.client.get("/transactions/new?kind=expense")
        self.assertIn(b'placeholder="0.00"', page.data)
        self.assertNotIn(b'value="0.00"', page.data)
        response = self.client.post("/transactions/new?kind=expense", data={
            "csrf_token": self.csrf(), "kind": "expense", "group_name": group_name,
            "category_id": category_id, "cash_date": date.today().isoformat(),
            "subtotal": "500,000.00",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            txn = Transaction.query.filter_by(subtotal=500000).one()
            self.assertEqual(float(txn.total), 500000)


if __name__ == "__main__":
    unittest.main()
