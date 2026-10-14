# KYS Finance company package

This package contains the server EXE, in-place CMD/PowerShell installer, desktop and sign-in startup shortcuts, Private-LAN firewall helper, client setup and external-backup configuration. It is not an MSI or single-file Setup.exe. Keep the entire extracted folder permanently in a writable location (for example Documents). Do not copy only the EXE.

## Server: Windows 7 SP1

1. For a clean Windows 7 installation, install Microsoft KB2999226 (Universal CRT) and KB3063858 (DLL loading), then restart. Choose the update architecture matching Windows, not the x86 application. Official x64 links: https://www.microsoft.com/en-us/download/details.aspx?id=49093 and https://www.microsoft.com/en-us/download/details.aspx?id=47442 . This package does not silently modify Windows runtime components.
2. Extract into a NEW permanent folder. Do not copy test databases, old demo databases or production databases into this package. Existing installations need a separate backed-up migration procedure.
3. Run Install Company Server.cmd as the normal Windows user who will run the server. Enter a NEW administrator username and matching password (minimum 12 characters). The password is not displayed. There are no seeded company/demo accounts in this build.
4. Approve the Windows administrator prompt for network rules. Only Private-network local-subnet TCP 5000 and UDP 5057 are allowed for this EXE. Select Home/Work on Windows 7 only for a trusted company network. Never disable the firewall or forward these ports to the internet.
5. The installer creates desktop shortcuts and a per-user Startup shortcut. Server startup occurs AFTER this Windows user signs in, not before sign-in; keep that session signed in. This does not log anyone into the finance application. Every user needs their own app credentials. Create staff accounts in Users & access.
6. Configure External Backup.cmd needs a real external drive/NAS destination selected by the company. Local backups alone do not protect against server disk loss. Validate a restore before admitting company data.

## Clients: Windows 7 / 10 / 11

Copy the client folder to each PC and run Install KYS Finance Client.cmd once. It creates a KYS Finance desktop shortcut and a sign-in discovery monitor. The client does not install a server or create a separate database. Open the shortcut on the trusted company network; if discovery is blocked, choose M and enter the server's LAN address and port 5000. Merely joining Wi-Fi does not install anything. Browser sessions still require app login. Windows 7 requires a compatible browser and remains unsupported by modern browser vendors.

## Data and safety

Overview, Cash ledger and Reports check for saved changes every five seconds while the tab is visible. New entries, edits, deletions and account/group changes refresh the current view with its applied month and filters. Unsaved filter selections and open delete confirmations defer refresh; use Show latest data to discard a pending selection and reload. Entry/edit forms do not auto-refresh. Network interruptions retry automatically. This display update is separate from database backups.

### Easy restore on the server computer

After completing installation, double-click **Restore KYS Backup** on the server desktop (or run **Restore KYS Backup.cmd** in the installed folder). Enter the current installation administrator username/password, choose the old `.db` file, review its transaction count and latest transaction date, and confirm. Restore replaces data and users; it does not merge two databases. The file must be from a compatible KYS database version and contain an active administrator.

The wizard stops this installation's server, creates a verified safety database and session-key copy under `restore-recovery`, restores the selected snapshot and restarts the server after the wizard closes. Sign in using credentials stored in the restored backup. Other users are disconnected and must sign in again. No manual `.secret_key` copying is required: restore creates a new session key. The original backup is preserved. If the backup is from an incompatible older schema, the wizard refuses it and a version migration is needed.

For an existing company installation, stop its server and replace the EXE, `_internal` and helper files with this release while preserving `data`, `backups`, `restore-recovery` and configuration. Rerun the installer from the SAME folder to add the Restore shortcut. Do not place a live database into a fresh unconfigured package; install first and use the wizard. Keep `restore-recovery` copies confidential and copy them off-PC if needed. An interrupted restore may leave `restore.lock`; inspect recovery copies and ensure no restore process is running before removing that lock.

Never distribute data/, backups/, .secret_key or backup-target.txt inside a release. The installer refuses an unrecognized database and does not overwrite another shortcut's installation. Preserve the entire live data folder before upgrading. Restore a backup into a separate clean recovery installation, never over a running database; migration/restore installation support requires IT validation.

HTTP is not encrypted. Use only an IT-approved restricted LAN, or have IT configure HTTPS before sensitive use. Windows 7 and Python 3.8 are out of support; this package cannot restore OS security support. Startup-folder launch has no crash-restart service.

## Acceptance status

Earlier legacy VM checks passed on Windows 7 SP1 x64 with the two Microsoft updates. A Windows 11 host connected to that VM with four read-only sessions. Those results do not certify this newly packaged company build. Final company-machine install, reboot, multi-user writes, external-drive restore and user acceptance must be verified before production handover. Actual Windows 7 32-bit and Windows 10 client checks remain pending unless separately recorded.
