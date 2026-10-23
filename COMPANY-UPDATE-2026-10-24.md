# K.Y.S. Finance — account chart update (24 October 2026)

The source chart is `Rearranged Particulars.xlsx`: 11 groups and 106 particulars. A new installation starts with this chart. An existing company installation keeps its database and must use the administrator's **Update account chart** page once after the application upgrade. That page previews all proposed changes, refuses an ambiguous or unmatched posted account, takes a verified database backup, and then relabels existing account records in one transaction. April transactions remain linked to the same internal records, so April reports show the revised names/codes without re-entry. Amounts and transaction count are checked before commit.

## Updating an existing company server

Do **not** run `KYS Finance Setup.exe` over a nonempty company folder. It is a fresh-install wizard and deliberately refuses that folder. Do not uninstall or restore an old snapshot merely to update the program.

1. Arrange a short maintenance window. Ask all users to save work and sign out. On the server, use the application's backup action and confirm the backup exists on the other PC. Keep a separate copy of the entire current installation for rollback, including `data`, `backups`, `.secret_key`, `backup-target.txt`, `kys-install.json`, and any `restore-recovery` folder.
2. Stop the company server with its Stop shortcut; verify that port 5000 and `KYS Finance Server.exe` have stopped. If the shortcut fails, have an administrator stop the process before replacing program files. Never replace a running database or executable.
3. From `release/company-win7/KYS Finance Server`, replace the **application** files in the existing server directory: `KYS Finance Server.exe`, `_internal`, scripts, client folder, icons, and documentation. Keep the existing `data`, `backups`, `restore-recovery`, `.secret_key`, `backup-target.txt`, `kys-install.json`, and installation markers untouched. If Windows refuses a file replacement, stop and resolve the running process; do not force deletion of company data.
4. Run `Install Company Server.ps1 -AccountConfigured` from that same folder as administrator, or use the existing start shortcut and verify the server URL. Do not create a new administrator or new database.
5. Sign in as an application administrator, open **Update account chart**, review the preview, then apply it once. If the page lists a posted account needing manual mapping (for example a duplicated or renamed `2700` account), stop there. Do not guess, delete, or merge that posted account. Confirm its intended workbook destination first.
6. Verify April P&L and ledger totals against the pre-update report, check a few account codes and entry counts, and have client users refresh/reopen the page. The client points to the same server; normally no client reinstall is needed for account-chart changes.

If the upgrade fails, stop the server and restore the *entire pre-upgrade installation* and its matching database/secret key from the separate safety copy. Avoid restoring an older DB over newer entries. Keep backup files private.

## Updating from home

There is currently **no remote auto-deployment** or automatic software-update feature. The browser's five-second data refresh only shows new ledger data; it does not install new code. Transfer the tested application package via an approved company remote-support channel or encrypted file transfer, then perform the server-side maintenance steps above with company administrator approval. Do not expose the app's plain HTTP port 5000 directly to the internet. Staff PCs continue using the company LAN/Wi-Fi server after its restart.
