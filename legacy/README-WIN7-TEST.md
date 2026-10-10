# Windows 7 SP1 legacy TEST candidate — not production-certified

This x86 build is intended for both 32-bit and 64-bit Windows 7 SP1. It uses Python 3.8.10 and older compatible dependencies. Windows 7 and Python 3.8 are out of support. Do NOT use confidential company data or expose this test server to the internet. It listens on localhost only; no LAN firewall rules are installed.

The revised launcher and executable were tested on a Windows 7 SP1 x64 VirtualBox VM on 2026-10-10. Startup after restart, health, login, disposable income/expenditure, report totals and Excel download passed. This is not certification of a 32-bit Windows installation or a company deployment. See TEST-RESULTS.md. Older published ZIPs may not contain these launcher fixes.

## Required Windows updates

On the tested clean Windows 7 SP1 VM, install Microsoft's Universal C Runtime update KB2999226 and DLL-loading update KB3063858, then restart Windows. Without them, Python can fail to load python38.dll or _socket before the application starts. Choose updates for the Windows OS architecture (not the x86 app architecture).

- x64 KB2999226: https://www.microsoft.com/en-us/download/details.aspx?id=49093
- x64 KB3063858: https://www.microsoft.com/en-us/download/details.aspx?id=47442

These links are for x64 Windows only. Do not obtain individual DLLs from random websites. Installing these prerequisites does not restore security support for Windows 7.

## Test on the actual Windows 7 PC

1. Back up any existing company data. Stop the old server. Extract this ZIP into a NEW, permanent, user-writable folder. Do not copy an existing database into it.
2. Run `Install Legacy Test.cmd` normally as the Windows user who will run it. It creates desktop and current-user Startup shortcuts in place. It does not upgrade another installation. Keep this folder in place.
3. Run `Check Legacy Server.cmd`. Send `compatibility-test.txt` and any error screenshot back to the developer. If it fails, also send `server-error.log` / `launcher-error.log`, not your database or secrets.
4. Sign in with the initial test account `admin` / `Admin@2026`, change the password, create disposable test income/expenditure, generate a report and export Excel. Verify totals. Do not use real company data.
5. Restart Windows, sign in as the same user and run ONLY `Check Legacy Server.cmd` (not Install/Start). Confirm the health check passes and disposable entries remain. This tests actual sign-in startup/persistence. It does not start before Windows sign-in.

Keep this PC awake while testing. The Startup-folder fallback has no crash-restart service. LAN deployment, external backup configuration and real-data migration need separate validation after these tests pass.

To disable test startup, remove only `KYS Finance Legacy TEST.lnk` from the current user's Startup folder (`Win+R`, `shell:startup`). Close the corresponding test server process before removing its extracted folder. Do not remove any production database.
