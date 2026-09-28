# K.Y.S. Cash-Based P&L Management System

A lightweight local-network accounting application for actual cash receipts and payments. It uses Flask, SQLAlchemy, SQLite, vanilla JavaScript, and Excel exports.

## Start on Windows

Use the [Windows server release](https://github.com/Roshadha/kys-finance-system/releases) for a Python-free deployment, then follow [COMPANY_SETUP.md](COMPANY_SETUP.md). The EXE runs only on the server PC; other computers use a browser shortcut. The installer enables auto-start when the server's Windows user signs in. Configure a separate USB/NAS backup location before entering company data.

To run from source instead:

1. Run `setup.bat` once on the host computer.
2. Run `start.bat` whenever the system should be available.
3. On the host computer, open `http://127.0.0.1:5000`.
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
- Trade Income entries use Sub total only. Record tax cash movements separately under the **Inward Taxes** income group or **Tax Expenditure** expenditure group, each with **SSCL** and **VAT** particulars. Both groups can be selected independently in report dropdowns.
- Saved ledger entries cannot be edited or deleted.
- Administrators correct entries through signed adjustments, preserving the original.
- Every sign-in, entry, adjustment, user change, export, and backup is written to audit history.
- Verified SQLite backups run when the server starts and every two hours while it is running. Administrators can create an immediate backup from the dashboard. A configured external drive/NAS receives a daily second copy for disaster recovery.
- Monthly and short summary reports can be filtered by income and expenditure groups and exported to Excel.

## Configuration

Set these optional environment variables before starting:

- `KYS_SECRET_KEY`: persistent, private Flask session key.
- `KYS_DATABASE_URL`: SQLAlchemy database URL. Defaults to the local SQLite database in `data/`.
- `KYS_HOST`: server bind address. Defaults to `0.0.0.0` for local-network access.
- `PORT`: server port. Defaults to `5000`.

For production use, set a strong persistent `KYS_SECRET_KEY`, protect the host with user accounts and disk backups, and restrict firewall access to the trusted local network.

To rebuild the Windows EXE on a 64-bit Windows server/development PC, install `pyinstaller` in `.venv` and run `build_exe.ps1`. It writes a one-folder bundle to `release/KYS Finance Server/`. Do not rebuild over a live `data/` folder.
