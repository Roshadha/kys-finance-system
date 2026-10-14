import os
import unittest
from datetime import date
from unittest.mock import patch
from html import unescape
import re

os.environ["KYS_DISABLE_BACKUP"] = "1"

from app import Adjustment, Category, Transaction, User, Group, AuditLog, build_report, group_codes, particular_codes, sorted_categories, seed_database, create_app, db


class FinanceAppTests(unittest.TestCase):
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

    def test_dashboard_month_links_follow_calendar_boundaries(self):
        class MarchFirst(date):
            @classmethod
            def today(cls):
                return cls(2024, 3, 1)

        self.login("recovery", "KysRec@2026")
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
