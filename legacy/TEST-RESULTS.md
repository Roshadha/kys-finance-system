# Legacy candidate test results — 2026-10-06

Build: Python 3.8.10 x86, PyInstaller 6.10.0, separate Cheroot entry point.
Test host: Windows 11 (build 26200), NOT Windows 7.

- 24 application tests passed on Python 3.8 x86: transactions/adjustments, reports/Excel, group filters, tax groups, backup behavior, account migration and discovery.
- 24 application tests passed on the modern Python runtime after the shared compatibility changes.
- Packaged EXE started using an isolated in-memory database. HTTP health and login-page checks passed.
- PE header confirmed x86 (0x014C). 30 packaged native binaries checked: no direct/delay import of api-ms-win-core-path-*.dll found. This narrow check does not validate all Windows 7 APIs or runtime prerequisites.
- Legacy PowerShell files parsed on development PowerShell. Windows PowerShell 2.0 execution, shortcut setup, Windows 7 boot/sign-in, target-machine memory usage, and browser behavior are NOT verified.
- No production database was used and no production startup/firewall configuration was changed.

## Actual VM checks — 2026-10-10

Target: Windows 7 Ultimate SP1 x64 (6.1.7601), Windows PowerShell 2.0, VirtualBox; separate disposable KYS-Test-20261009 folder. Host Windows was not updated.

- Fixed the launcher: PowerShell 2.0 cannot combine Start-Process WindowStyle with stream redirection. Use ProcessStartInfo/CreateNoWindow and Python-side logging instead.
- Installed official Microsoft KB2999226: resolved missing Universal CRT / python38.dll loader failure.
- Installed official Microsoft KB3063858 and restarted the VM: resolved _socket DLL loading failure (incorrect parameter).
- After restart, without manually starting the server, the HTTP test passed: health, admin login, income 1,250.00, expenditure 250.00, P/L 1,000.00, saved ledger entries, and Excel ZIP-signature download check.
- Test harness: vm_http_test.ps1. No production data used. Excel contents/layout were not visually inspected by this HTTP check.
- Repeated verification on 2026-10-10: existing entries passed before reboot; after a second graceful VM restart and Windows sign-in, the server started without a manual launch and the same entries, report totals and Excel download checks passed again. Saved transaction persistence across reboot is verified for this VM.
- Reran all 24 Python 3.8 x86 automated tests: passed on the development host using isolated databases. Initial sandbox attempts failed due to file/socket restrictions; the unrestricted test rerun passed. These are not 24 separate VM tests.
- Modern Windows launcher/autostart mock suites passed (hidden launch, duplicate/port conflict protection, delayed logon/retries and foreign-task protection). Mock results do not prove actual Windows 10 startup behavior.
- Not yet verified: actual 32-bit Windows OS, company LAN/multiple simultaneous clients, external backup restore on a replacement PC, production migration, browser layout, or long-running reliability. This remains a local-only TEST candidate, not approved for production handover.
- These changes have not yet been repackaged or uploaded to the existing GitHub prerelease.

## Host-to-VM network check — 2026-10-10

- Added host-only Adapter 2; NAT Adapter 1 preserved. Host 192.168.56.1, VM 192.168.56.101.
- A separate VM-only test launcher binds the app to the host-only address, not all interfaces. User applied the guest firewall rule permitting TCP 5000 only from 192.168.56.1 to 192.168.56.101.
- Four independent concurrent HTTP sessions from the Windows 11 host passed health, login, existing ledger entries, report totals (1250 income, 250 expense, 1000 P/L), and parsed Excel cell-value checks.
- This is concurrent reading from one physical client, not simultaneous transaction writes from multiple company PCs. Network-mode startup has not been installed; the original startup still uses localhost. Actual company LAN, Windows 7/10 client browser UI and off-PC restore remain unverified.
