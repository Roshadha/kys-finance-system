# K.Y.S. Finance — company setup

## One server PC

1. Copy the entire **KYS Finance Server** folder from the release ZIP onto a reliable Windows PC. Keep the EXE together with its `_internal` folder. Place it in a writable folder such as the server user's `Documents\KYS Finance Server`, not `Program Files`.
2. Double-click **KYS Finance Server.exe** on that PC. Keep its console window running while staff use the system. The server PC must remain powered on and connected to the company network.
3. Open `http://127.0.0.1:5000` on the server PC. The first run creates `data\kys_finance.db` and `data\.secret_key` beside the EXE. Passwords and transactions live in that database. Closing and reopening the EXE does not remove saved entries.
4. Find the server PC's LAN IPv4 address with `ipconfig` (for example `192.168.1.50`). Other PCs open `http://192.168.1.50:5000`. Set a static IP or DHCP reservation for this server so their shortcuts keep working.
5. Windows Firewall may need an inbound allow rule for TCP 5000 on the **Private** network. Ask the company's IT administrator to make this rule if clients cannot connect. Do not forward port 5000 to the internet.

## Other computers

They need only a current web browser and a shortcut. Do **not** install or run the EXE on each PC; doing that would create separate databases. To create a desktop shortcut on a client PC, copy `create-client-shortcut.ps1` to it and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\create-client-shortcut.ps1 -ServerAddress 192.168.1.50
```

Replace the sample address with the server PC's actual LAN IPv4 address. Or make a browser shortcut to `http://SERVER_IP:5000` manually. Users sign in with their own accounts and permissions.

## Data, backups, and updates

- The installed EXE stores live data in `data\kys_finance.db`, its session secret in `data\.secret_key`, and automatic SQLite backups in `backups\` beside the EXE. Backups run about every two hours **while the server is running**. Regularly copy backups to a separate drive or company-approved backup location as protection against disk failure.
- When updating, stop the server, back up `data\` and `backups\`, replace the EXE and `_internal` folder from the new release, and leave the existing `data\` and `backups\` folders in place.
- To move existing data from a previous copy of this app, stop both servers, copy its `data\kys_finance.db` and `data\.secret_key` into the release folder's `data\`, then start the EXE. Keep a backup of both folders before copying. Do not combine different database files by overwriting a live database.
- The initial demo login is `admin` / `Admin@2026`. Change all preset passwords immediately before using company data. This is an HTTP application intended for a trusted private LAN. Have IT assess network access and backups before putting sensitive finance data into production.

The 32-bit/2 GB client PC only uses a browser. The supplied Windows EXE is built for a 64-bit server PC.
