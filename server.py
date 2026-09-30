import os

from waitress import create_server

from discovery import start_discovery

from app import app


if __name__ == "__main__":
    host = os.environ.get("KYS_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    server = create_server(app, host=host, port=port, threads=4)
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
        if discovery:
            discovery[0].set()
            discovery[1].join(timeout=2)
        server.close()

