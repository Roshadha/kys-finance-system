import os
import sys

if '--copy-backup' in sys.argv:
    from backup_copy import main
    sys.exit(main(sys.argv[sys.argv.index('--copy-backup') + 1:]))

from waitress import create_server

from discovery import start_discovery

from app import app, DATA_ROOT, make_backup
from lifecycle import DrainGate, monitor_shutdown, prevent_sleep


if __name__ == "__main__":
    host = os.environ.get("KYS_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    gate = DrainGate(app)
    server = create_server(gate, host=host, port=port, threads=4)
    shutdown = monitor_shutdown(app, gate, DATA_ROOT, make_backup, server.close)
    prevent_sleep(True)
    discovery = None
    try:
        discovery = start_discovery(port, bind_host=host)
        print("Client auto-discovery enabled on UDP 5057.")
    except OSError as error:
        print(f"Auto-discovery unavailable ({error}); direct browser access still works.")
    print(f"K.Y.S. Finance is running on http://{host}:{port}")
    try:
        server.run()
    finally:
        shutdown.set()
        prevent_sleep(False)
        if discovery:
            discovery[0].set()
            discovery[1].join(timeout=2)
        server.close()

