# Legacy candidate test results — 2026-10-06

Build: Python 3.8.10 x86, PyInstaller 6.10.0, separate Cheroot entry point.
Test host: Windows 11 (build 26200), NOT Windows 7.

- 24 application tests passed on Python 3.8 x86: transactions/adjustments, reports/Excel, group filters, tax groups, backup behavior, account migration and discovery.
- 24 application tests passed on the modern Python runtime after the shared compatibility changes.
- Packaged EXE started using an isolated in-memory database. HTTP health and login-page checks passed.
- PE header confirmed x86 (0x014C). 30 packaged native binaries checked: no direct/delay import of api-ms-win-core-path-*.dll found. This narrow check does not validate all Windows 7 APIs or runtime prerequisites.
- Legacy PowerShell files parsed on development PowerShell. Windows PowerShell 2.0 execution, shortcut setup, Windows 7 boot/sign-in, target-machine memory usage, and browser behavior are NOT verified.
- No production database was used and no production startup/firewall configuration was changed.

Pending: execute the README test checklist on the actual Windows 7 SP1 machine. Until then this is a local-only TEST candidate, not a certified company server release.
