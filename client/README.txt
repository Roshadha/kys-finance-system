KYS FINANCE - CLIENT AUTO-DISCOVERY SETUP

1. Extract this whole ZIP into a folder on the staff PC.
2. Double-click Install KYS Finance Client.cmd once. Administrator access,
   Python and the server EXE are not required. Windows PowerShell 5.1 is used;
   both 32-bit and 64-bit Windows clients can use this helper.
3. Connect to the company Wi-Fi or wired LAN and open the KYS Finance desktop
   shortcut. Sign in with your own app account in the browser.

The helper is installed in %LOCALAPPDATA%\KYS Finance Client. Each time you open
the shortcut, it finds the server again, so a changed server IP is supported.
After Windows sign-in, a background check waits for the server every 30 seconds
and ensures the desktop shortcut exists once it is reachable. It stops after
finding the server. It does not open the browser automatically. On later network
changes, just open the shortcut to discover again.

If several servers are found, choose the correct company computer by name/IP.
Your selection is remembered. If that server disappears, the helper asks you
before switching to another discovered server. R retries; M enters a manual
server address when broadcasts are blocked; Q closes the launcher.

SERVER REQUIREMENTS
The server must use the Auto-Discovery release or newer. On the server, run
Enable Network Access.cmd once from the INSTALLED folder and approve Windows
administrator access. Use a trusted Private network profile. Discovery needs
UDP 5057 and the app needs TCP 5000. Both PCs must be on the same local subnet;
guest Wi-Fi isolation, VPNs, VLANs or company firewall rules can block discovery.
Ask IT if the company network prevents it. An ordinary Wi-Fi connection alone
cannot install software or a shortcut on a PC that has never run this setup.

The server must be on and running. Its current automatic startup happens AFTER
the installing Windows user signs in. It does not start before sign-in.
Only the server holds the database. Do not install the server EXE on staff PCs.
An existing older manual KYS Finance browser shortcut can remain; use the new
shortcut that briefly displays 'Looking for KYS Finance'.

TO REMOVE THE CLIENT HELPER
Close any open launcher. In Windows Task Manager, identify and stop only the
PowerShell process whose command line points to KYS Finance Client\KYS Client.ps1
with -Mode Monitor (if it is still waiting). Remove KYS Finance Client Discovery
from your user's Startup folder (Win+R, shell:startup), remove the desktop KYS
Finance .lnk shortcut, and remove %LOCALAPPDATA%\KYS Finance Client.
Removing this helper does not remove any server data.
