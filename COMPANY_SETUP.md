# K.Y.S. Finance — company setup

## One server PC

1. Extract the release ZIP, open the **KYS Finance Server** folder, and double-click **Install KYS Finance Server.cmd**. It copies the whole application to your `Documents\KYS Finance Server` folder and creates two desktop shortcuts. Keep the EXE together with its `_internal` folder; do not place it in `Program Files`.
2. Double-click **Start KYS Finance Server** on the server PC's desktop the first time. Keep its console window running while staff use the system. Then double-click **Open KYS Finance** to open the local browser page. Setup also registers **KYS Finance Server Auto Start** in Windows Task Scheduler (or uses the user's Startup folder if Task Scheduler is unavailable). After a restart, the server starts automatically **when that same Windows user signs in**. It does not start before sign-in. Keep that user signed in; lock the PC rather than signing out. If auto-start needs repairing on an existing installation, run **Enable Auto Start.cmd** from the installed folder. Before-sign-in operation requires an IT-managed Windows service account and is not enabled by this package.
3. Open `http://127.0.0.1:5000` on the server PC. The first run creates `data\kys_finance.db` and `data\.secret_key` beside the EXE. Passwords and transactions live in that database. Closing and reopening the EXE does not remove saved entries.
4. Find the server PC's LAN IPv4 address with `ipconfig` (for example `192.168.1.50`). Other PCs open `http://192.168.1.50:5000`. Set a static IP or DHCP reservation for this server so their shortcuts keep working.
5. Windows Firewall may need an inbound allow rule for TCP 5000 on the **Private** network. Ask the company's IT administrator to make this rule if clients cannot connect. Do not forward port 5000 to the internet.

## Other computers

They need only a current web browser and a shortcut. Do **not** install or run the EXE on each PC; doing that would create separate databases. On each client PC, copy **Create Client Shortcut.cmd** and `create-client-shortcut.ps1` from the server package into the same folder, then double-click the CMD file and enter the server PC's LAN IP address. It creates a **KYS Finance** browser shortcut on that client's desktop.

Alternatively, run the PowerShell helper directly:

```powershell
powershell -ExecutionPolicy Bypass -File .\create-client-shortcut.ps1 -ServerAddress 192.168.1.50
```

Replace the sample address with the server PC's actual LAN IPv4 address. Or make a browser shortcut to `http://SERVER_IP:5000` manually. All client shortcuts use the same server and database; users sign in with their own accounts and permissions. If the server's IP changes, recreate the shortcuts or ask IT for a stable IP/DHCP reservation.

## Data, backups, and updates

- The installed EXE stores live data in `data\kys_finance.db` and its session secret in `data\.secret_key`. It makes a verified SQLite snapshot in `backups\` when the server starts and about every two hours **while it is running**. The newest 60 local snapshots are kept. An administrator can also select **Back up database** in the app to create one immediately.
- Local backups are on the **same PC** and cannot protect against its disk being lost or destroyed. On the server PC, connect an external drive or arrange a company-approved NAS share, then run **Configure External Backup.cmd** from the installed folder and enter that folder's full path. It must be on a different drive/share. While available, the app copies one verified snapshot per day into `KYS-Finance-Backups\YYYY-MM-DD\` at that destination. Each completed folder contains `kys_finance.db`, `.secret_key`, and `backup-complete.txt`. A manual in-app backup creates an additional timestamped external folder. If the external location is unavailable, local backups continue, but the external copy fails; check the folder regularly. External copies are not automatically deleted, so monitor available space and apply the company's retention policy.
- The backup contains confidential financial data and a session secret. Restrict access to the external drive/share, encrypt it where appropriate, and keep a separate copy disconnected or in an approved off-site location. Test a restore on a spare PC periodically. Do not put live database files in GitHub or ordinary shared folders.
- When updating, stop the server, back up `data\` and `backups\`, replace the EXE, `_internal` folder, setup helpers, and this guide from the new release, and leave the existing `data\`, `backups\`, and `backup-target.txt` in place. The installer refuses to overwrite an existing installation to protect live data. If upgrading from an older release, run **Enable Auto Start.cmd** once and **Configure External Backup.cmd** once from the installed folder.
- To move existing data from a previous copy of this app, stop both servers, copy its `data\kys_finance.db` and `data\.secret_key` into the release folder's `data\`, then start the EXE. Keep a backup of both folders before copying. Do not combine different database files by overwriting a live database.
- The initial demo login is `admin` / `Admin@2026`. Change all preset passwords immediately before using company data. This is an HTTP application intended for a trusted private LAN. Have IT assess network access and backups before putting sensitive finance data into production.

## If the server fails

1. Keep the old server switched off so two PCs cannot accept different new entries. Choose the newest external backup folder containing `backup-complete.txt`. If the old disk is still readable, a newer `backups\kys_finance_*.db` may exist; preserve the entire old `data\` and `backups\` folders before doing anything else.
2. On a replacement **64-bit Windows** server PC, extract the latest release and run **Install KYS Finance Server.cmd**. Do **not** start its EXE yet. In its installed `Documents\KYS Finance Server\data\` folder, copy the backed-up `kys_finance.db` and `.secret_key` from the selected completed external backup. If that folder already contains a database, stop the server and move the existing `data\` folder to a clearly named safe location before copying—never overwrite a live database.
3. Start the EXE and sign in. Verify recent transactions, users, and a report before admitting other staff. Reconfigure the external backup location. Give the replacement server the old LAN IP through IT, or recreate client browser shortcuts using the new IP.
4. Entries made after the last completed backup may need to be re-entered from paper receipts or other records. If there is no off-PC backup and the old disk cannot be recovered, the app cannot reconstruct those entries.

The 32-bit/2 GB client PC only uses a browser. The supplied Windows EXE is built for a 64-bit server PC.
