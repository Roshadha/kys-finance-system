# Company package verification — 2026-10-10

- Python 3.8 x86: 25 regression tests passed, including four concurrent HTTP client sessions writing 12 transactions into isolated SQLite and restoring a backup to a separate application database. Recovered totals and parsed Excel values matched. The external backup destination was a separate temporary folder, not physical external storage.
- Additional administrator-bootstrap test passed: no demo accounts seeded in company mode; one locally chosen administrator; hashed password; old demo credentials rejected; reports require authentication.
- Company EXE built successfully with Python 3.8.10 x86 / PyInstaller 6.10.0.
- Actual Windows 7 SP1 x64 VM: company EXE loads with KB2999226 and KB3063858 and refuses unconfigured startup. PowerShell 2 client JSON, health check against the existing test server and shortcut creation passed.
- Earlier legacy build: two reboot/data-persistence checks and four Windows 11 host-to-Windows 7 VM read sessions passed. These are not full installer/reboot checks for this new company build.

Pending before production handover: interactively install this company build with the company owner's own administrator credentials and UAC firewall approval, reboot and verify new-package startup, actual company LAN/multiple physical clients, external-drive/NAS recovery, Windows 7 32-bit and Windows 10 client UI checks, and user acceptance. No claim of production certification or Windows 7 security support is made.

The deliverable is a ZIP with an EXE and CMD/PowerShell installer, not a signed standalone Setup.exe/MSI. No GitHub upload was performed for this build.

## Restore wizard update — 2026-10-12

Added a local administrator restore shortcut with a database file picker, transaction/date preview, explicit replacement confirmation, exact-installation process shutdown and startup interlock, verified pre-restore recovery copy, rollback on failure and session-key rotation. Original backup files are retained. Different database schemas are rejected rather than silently converted. No session-key file upload is needed.

All 30 automated tests passed, including four new restore tests for authentication/preview/recovery copies, corrupt backup rejection, missing-administrator rejection and rollback after a simulated session-key write failure. GUI runtime is bundled. The new wizard's end-to-end UI and stop/restart flow on Windows 7 still require acceptance testing; earlier VM checks refer to the preceding build.

## Clickable monthly chart — 2026-10-13

Overview chart bars and month labels now refresh Overview itself for the selected calendar month. Income, expenditure, P/L and the entries table use that month, with its label and selected chart highlight displayed. The chart calculates six consecutive calendar months correctly across year boundaries. Tests cover leap-year month links, access for entry users, empty-month display and inclusion/exclusion of transactions at month boundaries. Company-PC and Windows 7 VM acceptance testing for this update remains pending.

## Monthly posting and account management — 2026-10-13

35 automated tests passed. Added remembered Month/Year posting (new monthly entries store the first day), month selectors for Overview/ledger/reports, administrator deletion with required reason and retained audit records, editable numeric group ordering/name, hidden-group posting restrictions, and subtotal-only expenditure posting. SSCL/VAT remain separate tax particulars; fresh income codes are IP_0190/IP_0200. Existing account IDs and cash dates are preserved. Group ordering and deletion metadata use the existing audit table; no database schema migration is required. Deletes exclude the entire entry including adjustments from active reports. Windows 7 VM/company acceptance for this release remains pending.

## Direct amount editing — 2026-10-14

Pre-publication retest (2026-10-14): all 39 tests passed again. The four-client HTTP test now uses the actual restore_database engine on a separately initialized database, rather than copying files alone. Twelve entries totalling LKR 1,200 survive external-folder simulation backup, restore, subsequent login, reports and Excel export. This is not a real USB/NAS or physical company LAN test. JavaScript syntax verification passed. See BACKUP-GUIDE.md for Sinhala operator instructions and retention details.

Posting-period preference update: Month/Year changes on Income/Expenditure are saved immediately to per-user audit metadata via a CSRF-protected entry-permission endpoint, before a transaction is posted. The latest selection is shared across both entry forms and survives logout/restart; no database schema migration is needed. Successful entry submission also persists the chosen period. Overview's separate Month/Year/View month filter is removed; chart month links remain. Regression coverage includes per-user isolation, persistence across login, invalid months, CSRF, permissions, and no accidental transaction creation.

Report presentation update: 38 automated tests passed. Report sections and exported Summary follow the same administrator-editable numeric group-code order as selectors. Income remains before expenditure, and only matching posted accounts appear. Group Report export uses compact 20-point single-line rows (wrapping expands long labels), readable 11-point body text, contrasting 13-point section labels, and top/double-bottom rules for section totals and P/L. Monthly and Short Summary exports are covered by ordering/style tests. Browser particulars tables have larger text with reduced padding and corresponding heading/total emphasis. Existing financial calculations are unchanged.

Deletion UX update: Delete entry now displays a browser confirmation with the account and current cash total. Cancel leaves the entry untouched; confirmation posts a CSRF-protected administrator-only request without a reason field. A direct/no-JavaScript visit retains a confirmation-page fallback. Audit history records the administrator confirmation and removed total. Missing confirmation does not delete. The automated suite remains 37 tests.

37 automated tests passed. Ledger actions now offer separate Edit entry and Delete entry buttons. Administrators enter the correct cash total directly; the application records the difference internally without overwriting the original financial record. An edit audit records old/new totals and the mandatory reason. Tests cover decreases/increases, repeat submissions, stale forms, invalid values, permissions, CSRF, deleted entries and monthly report totals. SQLite edit requests acquire a write lock before reading the current version. This edits the cash total only, not the original subtotal/tax breakdown, month or account. Existing adjustment history and legacy adjustment routes remain compatible. Windows 7 VM/company acceptance testing of this update remains pending.

## Account code controls and simplified forms — 2026-10-13

Removed the Vehicle page, navigation, entry fields and ledger column. Legacy database vehicle references remain readable for backup compatibility. New Income and Expenditure forms now accept subtotal only; nonzero submitted tax fields are rejected. Separate tax particulars remain available. Public group codes start IG_0010/EG_0010 with step 10 and particular codes start IP_0100/EP_0100 with step 100. Existing internal database IDs remain stable; editable public codes are retained in audit metadata, used for numeric sorting and shown in selectors, reports and Excel exports. This supersedes the earlier displayed tax codes: default SSCL/VAT income display codes are now IP_1900/IP_2000. Administrators alone can set codes at creation or edit them later; duplicate codes within a type are rejected. Existing custom group code overrides remain preserved.
