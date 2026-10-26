# KYS Finance 2.0.0 — 26 October 2026

- Entry forms carry a persistent submission token. Retrying the same save returns the original result; reusing a token for changed data is rejected. Old forms must be refreshed once after updating.
- Automatic codes exclude the reserved legacy range (900000 and above). Custom chart accounts are kept by default. Legacy retirement is an explicit preview option; posted unmatched accounts and unresolved code conflicts stop that action.
- Administrators can set a 5–1440 minute backup interval in Backups (default 15). Each scheduled snapshot refreshes the configured other-PC copy. Local snapshots are retained for at least 30 days and the latest 60 files. External daily snapshots remain separate from manually requested copies. Backup failures are shown to administrators.
- Restore supports the recognized integer account-ID layout and missing user.deleted column through staged migrations. The original backup is not altered. Unknown schemas and newer schema versions remain blocked. Current schema version is 1.
- Optional company HTTPS is documented in HTTPS-SETUP.md. Activation requires a trusted company certificate and hostname.
- build-info.json identifies the source commit, build time and hashes used for the EXE. Databases, passwords, backup preferences and TLS keys are not shipped.

## Existing company installation

Back up the current live database, stop the server and preserve the complete old installation for rollback. Replace application files from the update ZIP. Preserve `data`, `backups`, `restore-recovery`, `.secret_key`, `backup-target.txt`, `backup-settings.json`, `backup-status.json`, `server-tls.json`, certificate/key files and installation markers. Restart and verify health, sign-in, entry count and reports. Do not run the fresh Setup EXE over a populated server directory.

This application update does not require reapplying the account chart. If a chart update is needed, use the default preserving preview and resolve code conflicts. Review legacy retirement separately only when intentionally retiring unused accounts.

