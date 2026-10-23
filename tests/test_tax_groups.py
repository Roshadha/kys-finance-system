import json
import unittest
from datetime import date
from urllib.parse import urlencode

import test_app
from app import Category, Group, Transaction, build_report, db, seed_database, group_codes, particular_codes


class TaxGroupTests(unittest.TestCase):
    login = test_app.FinanceAppTests.login
    csrf = test_app.FinanceAppTests.csrf

    def setUp(self):
        test_app.FinanceAppTests.setUp(self)
        self.login()

    def test_existing_database_is_not_silently_recoded_on_startup(self):
        with self.app.app_context():
            original = (Group.query.count(), Category.query.count())
            db.session.commit()
            seed_database()
            seed_database()
            self.assertEqual((Group.query.count(), Category.query.count()), original)

    def test_trade_income_uses_subtotal_only_and_tax_groups_report_separately(self):
        with self.app.app_context():
            trade = Category.query.filter_by(kind="income", group_name="Trade Income").first()
            inward = Category.query.filter_by(kind="income", group_name="Inward Taxes", name="Security Service Inward SSCL").one()
            outward = Category.query.filter_by(kind="expense", group_name="Outward Taxes", name="Security Service Outward VAT").one()
            ids = trade.id, inward.id, outward.id

        page = self.client.get("/transactions/new?kind=income")
        self.assertNotIn(b'id="sscl"', page.data)
        self.assertNotIn(b'id="vat"', page.data)
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
                ("expense", "Outward Taxes", ids[2], "80")):
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
                    json.dumps(["expense", "Outward Taxes"])]
            report = build_report(date.today(), date.today(), selected_groups=keys)
            self.assertEqual((report["income"], report["expense"], report["pl"]), (150, 80, 70))

        query = urlencode({"start": day, "end": day, "group": keys}, doseq=True)
        report_page = self.client.get("/reports?" + query)
        self.assertEqual(report_page.status_code, 200)
        self.assertIn(b'class="group-dropdown"', report_page.data)
        self.assertIn(b'Inward Taxes', report_page.data)
        self.assertIn(b'Outward Taxes', report_page.data)
        self.assertNotIn(b'Security Service Income', report_page.data.split(b'Income Particulars')[-1])
        export = self.client.get("/reports/export?" + query)
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.data[:2], b"PK")


class SequentialIdTests(unittest.TestCase):
    login = test_app.FinanceAppTests.login
    csrf = test_app.FinanceAppTests.csrf

    def setUp(self):
        test_app.FinanceAppTests.setUp(self)
        self.login()

    def test_seeded_ids_follow_the_sequence(self):
        with self.app.app_context():
            group_public = group_codes()
            particular_public = particular_codes()
            groups = {g.name: group_public[g.id] for g in Group.query.all()}
            self.assertEqual(groups["Trade Income"], 10)
            self.assertEqual(groups["Bank Interest Income"], 20)
            self.assertEqual(groups["Property Rental Income"], 30)
            self.assertEqual(groups["Direct Trade Expenditure"], 10)
            self.assertEqual(groups["Operational Expenditure"], 20)
            income = Category.query.filter_by(kind="income", name="Security Service Income").one()
            expense = Category.query.filter_by(kind="expense", name="Security Service Salary Expenditure").one()
            self.assertEqual(particular_public[income.id], 100)
            self.assertEqual(particular_public[expense.id], 100)
            all_ids = [c.id for c in Category.query.all()]
            self.assertEqual(len(all_ids), len(set(all_ids)))
            self.assertTrue(all(c.group_id for c in Category.query.all()))

    def test_new_group_and_particular_get_next_ids(self):
        with self.app.app_context():
            last_group = max(int(g.id[3:]) for g in Group.query.filter_by(kind="income").all())
            last_cat = max(int(c.id[3:]) for c in Category.query.filter_by(kind="income").all())
        self.client.post("/groups", data={"csrf_token": self.csrf(), "kind": "income", "name": "Other Income"})
        self.client.post("/categories", data={"csrf_token": self.csrf(), "kind": "income",
                                              "group_name": "Other Income", "name": "Misc receipt"})
        with self.app.app_context():
            group = Group.query.filter_by(name="Other Income").one()
            cat = Category.query.filter_by(name="Misc receipt").one()
            self.assertEqual(group.id, f"IG_{last_group + 100}")
            self.assertEqual(cat.id, f"IP_{last_cat + 10:04d}")
            self.assertEqual(cat.group_id, group.id)
