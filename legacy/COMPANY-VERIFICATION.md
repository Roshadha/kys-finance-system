# Company package verification — 2026-10-10

- Python 3.8 x86: 25 regression tests passed, including four concurrent HTTP client sessions writing 12 transactions into isolated SQLite and restoring a backup to a separate application database. Recovered totals and parsed Excel values matched. The external backup destination was a separate temporary folder, not physical external storage.
- Additional administrator-bootstrap test passed: no demo accounts seeded in company mode; one locally chosen administrator; hashed password; old demo credentials rejected; reports require authentication.
- Company EXE built successfully with Python 3.8.10 x86 / PyInstaller 6.10.0.
- Actual Windows 7 SP1 x64 VM: company EXE loads with KB2999226 and KB3063858 and refuses unconfigured startup. PowerShell 2 client JSON, health check against the existing test server and shortcut creation passed.
- Earlier legacy build: two reboot/data-persistence checks and four Windows 11 host-to-Windows 7 VM read sessions passed. These are not full installer/reboot checks for this new company build.

Pending before production handover: interactively install this company build with the company owner's own administrator credentials and UAC firewall approval, reboot and verify new-package startup, actual company LAN/multiple physical clients, external-drive/NAS recovery, Windows 7 32-bit and Windows 10 client UI checks, and user acceptance. No claim of production certification or Windows 7 security support is made.

The deliverable is a ZIP with an EXE and CMD/PowerShell installer, not a signed standalone Setup.exe/MSI. No GitHub upload was performed for this build.
