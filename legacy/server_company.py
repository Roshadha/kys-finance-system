"""Company entry point: no public/default-user bootstrap endpoint."""
import os
import sys
import json
import getpass
from pathlib import Path

os.environ['KYS_COMPANY_MODE'] = '1'
configure = '--configure-admin' in sys.argv
if configure:
    os.environ['KYS_DISABLE_BACKUP'] = '1'
if getattr(sys, 'frozen', False) and not configure:
    root = Path(sys.executable).resolve().parent
    sys.stdout = open(str(root / 'server-startup.log'), 'a', buffering=1, encoding='utf-8')
    sys.stderr = open(str(root / 'server-error.log'), 'a', buffering=1, encoding='utf-8')

from app import app, db, User, TASKS
from cheroot.wsgi import Server
from discovery import start_discovery

if __name__ == '__main__':
    with app.app_context():
        if configure:
            if User.query.first():
                print('Existing accounts preserved. Use your current administrator login.')
                sys.exit(0)
            print('Create the company administrator. No default login is installed.')
            username = input('Administrator username: ').strip()
            if not username or len(username) > 80:
                sys.exit('A username of 1-80 characters is required.')
            password = getpass.getpass('New password (at least 12 characters): ')
            confirm = getpass.getpass('Confirm password: ')
            if len(password) < 12 or password != confirm:
                sys.exit('Passwords must match and contain at least 12 characters.')
            user = User(username=username, display_name='Company Administrator', department='Accounts',
                        role='admin', tasks_json=json.dumps(list(TASKS)))
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print('Administrator created. Staff accounts must be created in Users & access.')
            sys.exit(0)
        if not User.query.filter_by(role='admin', active=True).first():
            sys.exit('Setup incomplete: run Install Company Server.cmd to create an administrator.')
    host = os.environ.get('KYS_HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    server = Server((host, port), app, numthreads=4)
    discovery = None
    try:
        discovery = start_discovery(port, bind_host=host)
        server.start()
    finally:
        if discovery:
            discovery[0].set()
            discovery[1].join(timeout=2)
        server.stop()
