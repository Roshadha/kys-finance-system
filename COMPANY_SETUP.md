# K.Y.S. Finance — company setup

## One server PC

1. Extract the release ZIP, open the **KYS Finance Server** folder, and double-click **Install KYS Finance Server.cmd**. It copies the whole application to your `Documents\KYS Finance Server` folder and creates two desktop shortcuts. Keep the EXE together with its `_internal` folder; do not place it in `Program Files`.
2. Double-click **Start KYS Finance Server** on the server PC's desktop. Keep its console window running while staff use the system. Then double-click **Open KYS Finance** to open the local browser page. The server PC must remain powered on and connected to the company network. The server does not automatically start after a restart; use its desktop shortcut each time.
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

- The installed EXE stores live data in `data\kys_finance.db`, its session secret in `data\.secret_key`, and automatic SQLite backups in `backups\` beside the EXE. Backups run about every two hours **while the server is running**. Regularly copy backups to a separate drive or company-approved backup location as protection against disk failure.
- When updating, stop the server, back up `data\` and `backups\`, replace the EXE and `_internal` folder from the new release, and leave the existing `data\` and `backups\` folders in place. The installer refuses to overwrite an existing installation to protect live data.
- To move existing data from a previous copy of this app, stop both servers, copy its `data\kys_finance.db` and `data\.secret_key` into the release folder's `data\`, then start the EXE. Keep a backup of both folders before copying. Do not combine different database files by overwriting a live database.
- The initial demo login is `admin` / `Admin@2026`. Change all preset passwords immediately before using company data. This is an HTTP application intended for a trusted private LAN. Have IT assess network access and backups before putting sensitive finance data into production.

The 32-bit/2 GB client PC only uses a browser. The supplied Windows EXE is built for a 64-bit server PC.
