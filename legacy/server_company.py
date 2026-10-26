"""Company entry point: no public/default-user bootstrap endpoint."""
import os
import sys
import json
import getpass
from pathlib import Path

if '--copy-backup' in sys.argv:
    from backup_copy import main
    sys.exit(main(sys.argv[sys.argv.index('--copy-backup') + 1:]))

if '--restore' in sys.argv:
    from backup_restore import wizard
    wizard(Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent)
    sys.exit(0)
if (Path(sys.executable).resolve().parent / 'restore.lock').exists():
    sys.exit('Database restore in progress. Start the server after restore completes.')

os.environ['KYS_COMPANY_MODE'] = '1'
configure = any(flag in sys.argv for flag in ('--configure-admin', '--configure-admin-json', '--check-admin', '--backup-before-stop'))
if configure:
    os.environ['KYS_DISABLE_BACKUP'] = '1'
if getattr(sys, 'frozen', False) and not configure:
    root = Path(sys.executable).resolve().parent
    sys.stdout = open(str(root / 'server-startup.log'), 'a', buffering=1, encoding='utf-8')
    sys.stderr = open(str(root / 'server-error.log'), 'a', buffering=1, encoding='utf-8')

from app import app, db, User, TASKS, make_backup
from cheroot.wsgi import Server
from discovery import start_discovery
from lifecycle import DrainGate, monitor_shutdown, prevent_sleep
from app import DATA_ROOT
from server_security import tls_adapter

if __name__ == '__main__':
    with app.app_context():
        if configure:
            if '--backup-before-stop' in sys.argv:
                if not User.query.filter_by(role='admin', active=True).first():
                    sys.exit('No active administrator; backup refused.')
                path, external_path, external_error = make_backup(app, local_only=True)
                if external_error:
                    sys.exit('Local backup created, but the configured external backup failed: ' + external_error)
                print('Verified backup: ' + str(external_path or path))
                sys.exit(0)
            if '--check-admin' in sys.argv:
                sys.exit(0 if User.query.filter_by(role='admin', active=True).first() else 1)
            if User.query.first():
                if User.query.filter_by(role='admin', active=True).first():
                    print('Existing accounts preserved. Use your current administrator login.')
                    sys.exit(0)
                sys.exit('No active administrator. Restore or recover this installation first.')
            if '--configure-admin-json' in sys.argv:
                credentials = json.load(sys.stdin)
                username = credentials.get('username', '').strip()
                password = credentials.get('password', '')
                confirm = password
            else:
                print('Create the company administrator. No default login is installed.')
                username = input('Administrator username: ').strip()
                password = getpass.getpass('New password (at least 6 characters): ')
                confirm = getpass.getpass('Confirm password: ')
            if not username or len(username) > 80:
                sys.exit('A username of 1-80 characters is required.')
            if len(password) < 6 or password != confirm:
                sys.exit('Passwords must match and contain at least 6 characters.')
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
    gate = DrainGate(app)
    server = Server((host, port), gate, numthreads=4)
    adapter = tls_adapter(DATA_ROOT)
    if adapter:
        server.ssl_adapter = adapter
        app.config['SESSION_COOKIE_SECURE'] = True
    discovery = None
    shutdown = monitor_shutdown(app, gate, DATA_ROOT, make_backup, server.stop)
    prevent_sleep(True)
    try:
        try:
            if not adapter:
                discovery = start_discovery(port, bind_host=host)
        except OSError as error:
            print('Discovery unavailable; direct server address remains available: ' + str(error), file=sys.stderr)
        server.start()
    finally:
        shutdown.set()
        prevent_sleep(False)
        if discovery:
            discovery[0].set()
            discovery[1].join(timeout=2)
        server.stop()
