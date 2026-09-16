import os
import unittest
from datetime import date

os.environ["KYS_DISABLE_BACKUP"] = "1"

from app import Adjustment, Category, Transaction, User, create_app, db


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

    def test_locked_transaction_adjustment_and_excel_export(self):
        self.login()
        with self.app.app_context():
            category_id = Category.query.filter_by(code="351", kind="income").first().id
        response = self.client.post("/transactions/new?kind=income", data={
            "csrf_token": self.csrf(), "kind": "income", "category_id": category_id,
            "cash_date": date.today().isoformat(), "reference": "TEST-001",
            "counterparty": "Test Customer", "description": "Cash receipt",
            "subtotal": "100000", "sscl": "2500", "vat": "18000",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            txn = Transaction.query.filter_by(reference="TEST-001").one()
            self.assertEqual(float(txn.total), 120500)
            txn_id = txn.id
        response = self.client.post(f"/transactions/{txn_id}/adjust", data={
            "csrf_token": self.csrf(), "effective_date": date.today().isoformat(),
            "amount": "-5000", "reason": "Invoice value correction",
        })
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(Adjustment.query.filter_by(transaction_id=txn_id).count(), 1)
            self.assertEqual(db.session.get(Transaction, txn_id).adjusted_total, 115500)
        export = self.client.get(f"/reports/export?type=monthly&start={date.today()}&end={date.today()}")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.data[:2], b"PK")

    def test_data_entry_task_restrictions(self):
        self.login("recovery", "KysRec@2026")
        self.assertEqual(self.client.get("/transactions/new?kind=income").status_code, 200)
        self.assertEqual(self.client.get("/transactions/new?kind=expense").status_code, 403)
        self.assertEqual(self.client.get("/reports").status_code, 403)


if __name__ == "__main__":
    unittest.main()
