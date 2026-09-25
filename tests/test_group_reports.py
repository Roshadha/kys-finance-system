import json
import unittest
from datetime import date
from io import BytesIO
from urllib.parse import urlencode

from openpyxl import load_workbook
import test_app
from app import Category, Group, Transaction, Adjustment, db, build_report


class GroupReportTests(unittest.TestCase):
    login = test_app.FinanceAppTests.login
    csrf = test_app.FinanceAppTests.csrf

    def setUp(self):
        test_app.FinanceAppTests.setUp(self)
        self.login()
        self.day = date(2026, 9, 12)
        self.keys = [json.dumps([kind, 'Custom group']) for kind in ('income', 'expense')]
        with self.app.app_context():
            for kind, amount in [('income', 115), ('expense', 40)]:
                db.session.add(Group(kind=kind, name='Custom group', active=False))
                cat = Category(kind=kind, group_name='Custom group', code='999', name=kind + ' account', active=False)
                db.session.add(cat)
                db.session.flush()
                txn = Transaction(category_id=cat.id, cash_date=self.day, reference=kind,
                                  counterparty='Test', subtotal=amount - 15, sscl=5, vat=10,
                                  total=amount, created_by_id=1)
                db.session.add(txn)
                db.session.flush()
                if kind == 'income':
                    db.session.add(Adjustment(transaction_id=txn.id, effective_date=self.day,
                                              amount=-5, reason='Correction', created_by_id=1))
            db.session.add(Category(kind='income', group_name='Custom group', code='999', name='Zero account'))
            other = Category.query.filter_by(code='351').first()
            db.session.add(Transaction(category_id=other.id, cash_date=self.day, reference='excluded',
                                       counterparty='Other', subtotal=800, total=800, created_by_id=1))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def query(self, groups=None, report_type='monthly'):
        return urlencode({'start': str(self.day), 'end': str(self.day), 'type': report_type,
                          'group': self.keys if groups is None else groups}, doseq=True)

    def test_multi_group_totals_and_duplicate_codes(self):
        with self.app.app_context():
            report = build_report(self.day, self.day, selected_groups=self.keys)
            self.assertEqual((report['income'], report['expense'], report['pl']), (110, 40, 70))
            items = report['sections'][0]['groups'][0]['items']
            self.assertEqual(len(items), 1)
            self.assertEqual(sum(i['amounts']['Cash Total'] for i in items), 110)
            single = build_report(self.day, self.day, selected_groups=[self.keys[0]])
            self.assertEqual(single['expense'], 0)
            self.assertFalse(single['sections'][1]['groups'])
            empty = build_report(date(2020, 1, 1), date(2020, 1, 1), selected_groups=self.keys)
            self.assertEqual(empty['pl'], 0)
            self.assertFalse(empty['sections'][0]['groups'])

    def test_html_and_export_share_selection(self):
        response = self.client.get('/reports?' + self.query())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Zero account', response.data)
        self.assertNotIn(b'excluded', response.data)
        export = self.client.get('/reports/export?' + self.query())
        self.assertEqual(export.status_code, 200)
        wb = load_workbook(BytesIO(export.data))
        self.assertEqual(wb.sheetnames, ['Group Report', 'Summary', 'Detailed Ledger'])
        rows = list(wb['Group Report'].values)
        profit_row = next(row for row in rows if row[1] == 'Liquid P/L')
        self.assertEqual(profit_row[-1], 70)
        self.assertEqual(rows[4], ('No.', 'Particular', 'A/C code', 'Amount (LKR)', 'Total (LKR)'))
        labels = [row[1] for row in rows]
        self.assertLess(labels.index('Total Income'), labels.index('Expenditure Particulars'))
        self.assertLess(labels.index('Total Expenditure'), labels.index('Liquid P/L'))
        self.assertIn((1, 'income account', '999', 110, None), rows)
        html = response.data.decode()
        self.assertLess(html.index('Income Particulars'), html.index('Expenditure Particulars'))
        self.assertLess(html.index('class="report-strip"'), html.index('Income Particulars'))
        self.assertIn('class="group-picker" open', html)
        self.assertIn('Custom group', rows[3][0])
        self.assertNotIn('excluded', str(list(wb['Detailed Ledger'].values)))
        short = self.client.get('/reports/export?' + self.query(report_type='short'))
        wb = load_workbook(BytesIO(short.data))
        self.assertNotIn('Detailed Ledger', wb.sheetnames)
        self.assertNotIn('Zero account', str(list(wb['Group Report'].values)))
        short_rows = list(wb['Group Report'].values)
        self.assertEqual(sum(row[0] == 'Custom group' for row in short_rows), 2)
        self.assertIn(('Liquid P/L', 70), short_rows)
        short_html = self.client.get('/reports?' + self.query(report_type='short')).data
        self.assertNotIn(b'income account', short_html)
        self.assertNotIn(b'Custom group \xe2\x80\x94 Total', short_html)
        self.assertNotIn(b'<option value="direct"', response.data)

    def test_invalid_group_and_report_types(self):
        for path in ['/reports', '/reports/export']:
            self.assertEqual(self.client.get(path + '?' + self.query(['invalid'])).status_code, 400)
        for report_type in ['monthly', 'short', 'direct', 'rental', 'construction']:
            self.assertEqual(self.client.get('/reports?' + self.query(report_type=report_type)).status_code, 200)
        self.assertEqual(self.client.get('/reports?' + self.query([])).status_code, 200)
