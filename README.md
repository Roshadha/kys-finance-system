# K.Y.S. Cash-Based P&L Management System

A lightweight local-network accounting application for actual cash receipts and payments. It uses Flask, SQLAlchemy, SQLite, vanilla JavaScript, and Excel exports.

## Start on Windows

1. Run `setup.bat` once on the host computer.
2. Run `start.bat` whenever the system should be available.
3. On the host computer, open `http://0.0.0.0:5000
4. Other computers on the same local network can use `http://HOST_IP:5000`.

The host computer may need a Windows Firewall rule allowing private-network access to TCP port 5000.

## Initial accounts

| Role | Username | Temporary password |
|---|---|---|
| Administrator | `admin` | `Admin@2026` |
| Management | `management` | `Manage@2026` |
| Recovery data entry | `recovery` | `KysRec@2026` |

Change all temporary passwords immediately from the settings icon after signing in.

## Accounting controls

- Cash date is the date money was actually received or paid.
- Saved ledger entries cannot be edited or deleted.
- Administrators correct entries through signed adjustments, preserving the original.
- Every sign-in, entry, adjustment, user change, export, and backup is written to audit history.
- Automatic SQLite backups run every two hours while the server is running. Administrators can also create an immediate backup from the dashboard.
- Excel reports include summary and detailed ledger sheets and can be manually adjusted after download.

## Configuration

Set these optional environment variables before starting:

- `KYS_SECRET_KEY`: persistent, private Flask session key.
- `KYS_DATABASE_URL`: SQLAlchemy database URL. Defaults to the local SQLite database in `data/`.
- `KYS_HOST`: server bind address. Defaults to `0.0.0.0` for local-network access.
- `PORT`: server port. Defaults to `5000`.

For production use, set a strong persistent `KYS_SECRET_KEY`, protect the host with user accounts and disk backups, and restrict firewall access to the trusted local network.

