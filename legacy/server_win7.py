"""Windows 7 legacy test entry point; does not alter the modern Waitress server."""
import os
from cheroot.wsgi import Server
from app import app
from discovery import start_discovery

if __name__ == '__main__':
    host = os.environ.get('KYS_HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    server = Server((host, port), app, numthreads=4)
    discovery = None
    try:
        discovery = start_discovery(port, bind_host=host)
    except OSError as error:
        print('Discovery unavailable: {}'.format(error))
    try:
        print('LEGACY TEST BUILD - http://{}:{}'.format(host, port))
        server.start()
    finally:
        if discovery:
            discovery[0].set()
            discovery[1].join(timeout=2)
        server.stop()
