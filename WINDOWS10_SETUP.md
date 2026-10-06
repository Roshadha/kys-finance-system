# Windows 10 lightweight packages

Choose x86 for 32-bit Windows and x64 for 64-bit Windows. These are server packages: install only ONE server for a shared company database. Other PCs use the client/browser shortcut; do not install another server for the same company.

Extract the complete package. For a fresh install, run `Install KYS Finance Server.cmd` normally using the Windows account that will remain signed in. Approve only the firewall elevation prompt. Do not run the entire installer as another administrator account: that would configure startup for that other account.

For an existing installation: first back up its data and stop the server. Copy the new EXE, `_internal`, and helper files into that installation, retaining `data`, `backups` and `backup-target.txt`. Run `Install KYS Finance Server.cmd` there. Do not overwrite or delete company data. Do not move the installed folder afterward.

## Startup repair

Run `Enable Auto Start.cmd` from the actual installed folder while signed in as the intended server user. It re-registers and enables the task. A conflicting task pointing to a different installation is deliberately not overwritten: inspect that older installation and its data first.

The scheduled task starts about 30 seconds AFTER that Windows user signs in. It does not run before sign-in, after signing out, or while the computer sleeps. Lock the screen instead of signing out. If registration is unavailable, setup explicitly reports a Startup-folder fallback. Do not disable the task or fallback in Windows startup settings.

On slow machines setup waits longer for the first health check. Task failures retry up to 10 times at one-minute intervals. Check `launcher-error.log`, `server-error.log` and `server-startup.log` in the installed folder if the app does not start. In Task Scheduler, inspect `KYS Finance Server Auto Start`, its configured user, action path and Last Run Result. Send those details for diagnosis; a specific remote-PC failure cannot be inferred just from the Windows version.

## Resource usage

Excel exports now use openpyxl directly. pandas and NumPy are excluded from both builds, reducing package size and startup imports without removing reports. Hardware performance depends on transaction count, simultaneous users, RAM and disk speed; this is not a guarantee for every low-end PC.

Both executable architectures are smoke-tested on the development host. Actual Windows 10 reboot and low-memory hardware tests must still be performed on the target PCs. These packages are not Windows 7 builds.

Local backups are automatic while the server runs. Configure a separate external backup destination for protection against server disk failure.
