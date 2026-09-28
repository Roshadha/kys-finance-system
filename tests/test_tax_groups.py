import json
import unittest
from datetime import date
from urllib.parse import urlencode

import test_app
from app import Category, Group, Transaction, build_report, db, seed_database


class TaxGroupTests(unittest.TestCase):
    login = test_app.FinanceAppTests.login
    csrf = test_app.FinanceAppTests.csrf

    def setUp(self):
        test_app.FinanceAppTests.setUp(self)
        self.login()

    def test_new_groups_are_added_to_existing_database_once(self):
        with self.app.app_context():
            for kind, group in (("income", "Inward Taxes"), ("expense", "Tax Expenditure")):
                Category.query.filter_by(kind=kind, group_name=group).delete()
                Group.query.filter_by(kind=kind, name=group).delete()
            db.session.commit()
            seed_database()
            seed_database()
            for kind, group in (("income", "Inward Taxes"), ("expense", "Tax Expenditure")):
                self.assertEqual(Group.query.filter_by(kind=kind, name=group).count(), 1)
                self.assertEqual({c.name for c in Category.query.filter_by(kind=kind, group_name=group)},
                                 {"SSCL", "VAT"})

    def test_trade_income_uses_subtotal_only_and_tax_groups_report_separately(self):
        with self.app.app_context():
            trade = Category.query.filter_by(kind="income", group_name="Trade Income").first()
            inward = Category.query.filter_by(kind="income", group_name="Inward Taxes", name="SSCL").one()
            outward = Category.query.filter_by(kind="expense", group_name="Tax Expenditure", name="VAT").one()
            ids = trade.id, inward.id, outward.id

        page = self.client.get("/transactions/new?kind=income")
        self.assertIn(b'data-subtotal-only="1"', page.data)
        self.assertIn(b'Inward Taxes', page.data)
        day = date.today().isoformat()
        invalid = self.client.post("/transactions/new?kind=income", data={
            "csrf_token": self.csrf(), "kind": "income", "group_name": "Trade Income",
            "category_id": ids[0], "cash_date": day, "subtotal": "1000", "vat": "150",
        })
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b"separate tax particulars", invalid.data)

        for kind, group, category_id, amount in (
                ("income", "Trade Income", ids[0], "1000"),
                ("income", "Inward Taxes", ids[1], "150"),
                ("expense", "Tax Expenditure", ids[2], "80")):
            response = self.client.post(f"/transactions/new?kind={kind}", data={
                "csrf_token": self.csrf(), "kind": kind, "group_name": group,
                "category_id": category_id, "cash_date": day, "subtotal": amount,
            })
            self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            trade_entry = Transaction.query.filter_by(category_id=ids[0]).one()
            self.assertEqual((float(trade_entry.total), float(trade_entry.sscl), float(trade_entry.vat)),
                             (1000, 0, 0))
            keys = [json.dumps(["income", "Inward Taxes"]),
                    json.dumps(["expense", "Tax Expenditure"])]
            report = build_report(date.today(), date.today(), selected_groups=keys)
            self.assertEqual((report["income"], report["expense"], report["pl"]), (150, 80, 70))

        query = urlencode({"start": day, "end": day, "group": keys}, doseq=True)
        report_page = self.client.get("/reports?" + query)
        self.assertEqual(report_page.status_code, 200)
        self.assertIn(b'class="group-dropdown"', report_page.data)
        self.assertIn(b'Inward Taxes', report_page.data)
        self.assertIn(b'Tax Expenditure', report_page.data)
        self.assertNotIn(b'Security Service Income', report_page.data.split(b'Income Particulars')[-1])
        export = self.client.get("/reports/export?" + query)
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.data[:2], b"PK")
