# Group reporting update

## Install into an existing application

Stop the server and back up your existing application before replacing these files:

- `app.py`
- `templates/reports.html`
- `static/reports.css` (new)

Keep your existing `data/`, `.secret_key`, backups and environment settings. This update needs no database migration and uses the Groups and Categories already in your supplied application. Restart with `start.bat`.

## Generate a report

Open **P&L reports**, choose a report type and dates, expand **Groups**, and tick one or more income and/or expenditure groups. Click **Generate**. Uncheck all groups to include all groups. **Export Excel** downloads the last generated selection, even if you have subsequently changed the form without pressing Generate.

The Monthly statement lists all Income groups and Total Income first, then all Expenditure groups and Total Expenditure. Columns are row number, particular, A/C code, cash amount and group/section total. Bold group headings sit above their particulars. The final calculation is Total Liquid Income minus Total Expenditure equals Liquid P/L. Amounts include recorded taxes and adjustments; their component breakdown remains in the Excel Detailed Ledger. Only accounts with cash entries in the selected period appear; empty groups are omitted. An account with recorded entries that net to zero remains visible. Existing disabled groups remain selectable for historical reporting.

The selector offers Monthly Cash-Based P&L and Short Summary P&L only. Short Summary shows each group name and amount once under Income or Expenditure, without account lines. Excel follows the same layout in **Group Report**, with a **Summary** sheet and (Monthly only) a filtered **Detailed Ledger** sheet. Income-only or expenditure-only selections produce P/L for that selection, not the entire business.

Existing cash date and adjustment calculations are unchanged by this update. Adjustments follow the original transaction's report period, as in the supplied version.

## Verification

Run `python -m unittest discover -s tests -v` after installing requirements. Group tests cover multiple selections, the same group name on both sides, duplicate account codes, disabled groups, zero balances, invalid filters, the monthly and short report types, and the exported workbook totals.
