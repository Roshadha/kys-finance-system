"""Local administrator restore wizard. Financial writes require a stopped server."""
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from werkzeug.security import check_password_hash


def connect_readonly(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def inspect_backup(path, current):
    with closing(connect_readonly(path)) as source, closing(connect_readonly(current)) as target:
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('This backup is damaged. Choose another backup.')
        if source.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('This backup contains broken record links.')
        if source.execute("SELECT name FROM sqlite_master WHERE type IN ('trigger','view')").fetchone():
            raise ValueError('This file contains unsupported database objects.')
        tables = [row[0] for row in target.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            expected = [(row[1], row[2], row[5]) for row in target.execute('PRAGMA table_info(' + quoted + ')')]
            actual = [(row[1], row[2], row[5]) for row in source.execute('PRAGMA table_info(' + quoted + ')')]
            if expected != actual:
                raise ValueError('This backup uses a different database version. It needs a version migration before restore.')
        admins = source.execute("SELECT COUNT(*) FROM user WHERE role='admin' AND active=1").fetchone()[0]
        if not admins:
            raise ValueError('This backup has no active administrator account.')
        count, latest = source.execute('SELECT COUNT(*), MAX(cash_date) FROM "transaction"').fetchone()
        return count, latest or 'No transactions'


def authenticate(path, username, password):
    with closing(connect_readonly(path)) as connection:
        row = connection.execute("SELECT password_hash FROM user WHERE lower(username)=lower(?) AND role='admin' AND active=1", (username,)).fetchone()
        return bool(row and check_password_hash(row[0], password))


def restore_database(staged, root):
    """Caller holds restore.lock and has stopped the exact installation's server."""
    root = Path(root)
    live = root / 'data' / 'kys_finance.db'
    inspect_backup(staged, live)
    recovery = root / 'restore-recovery' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    recovery.mkdir(parents=True)
    secret = root / 'data' / '.secret_key'
    with closing(sqlite3.connect(str(live))) as source, closing(sqlite3.connect(str(recovery / 'kys_finance.db'))) as backup:
        source.backup(backup)
        if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Safety backup verification failed. Restore cancelled.')
    if secret.exists():
        shutil.copy2(secret, recovery / '.secret_key')
    try:
        with closing(connect_readonly(staged)) as source, closing(sqlite3.connect(str(live))) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Restored database validation failed.')
        # Invalidate sessions from the replaced user database; old secret not needed.
        temporary = secret.with_name('.secret_key.restore-tmp')
        temporary.write_text(secrets.token_hex(32), encoding='utf-8')
        os.replace(str(temporary), str(secret))
    except Exception:
        with closing(connect_readonly(recovery / 'kys_finance.db')) as source, closing(sqlite3.connect(str(live))) as target:
            source.backup(target)
        if (recovery / '.secret_key').exists():
            shutil.copy2(recovery / '.secret_key', secret)
        raise
    return recovery


def wizard(root):
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
    root = Path(root).resolve()
    window = tk.Tk()
    window.withdraw()
    live = root / 'data' / 'kys_finance.db'
    lock = root / 'restore.lock'
    locked = False
    restart = False
    try:
        if not live.exists() or not (root / 'setup-complete.txt').exists():
            raise ValueError('Complete Install Company Server first, then open Restore KYS Backup.')
        username = simpledialog.askstring('Restore KYS Backup', 'Current installation administrator username:', parent=window)
        if username is None:
            return
        password = simpledialog.askstring('Administrator verification', 'Current administrator password:', show='*', parent=window)
        if password is None:
            return
        if not authenticate(live, username, password):
            raise ValueError('Administrator username or password is incorrect.')
        chosen = filedialog.askopenfilename(title='Choose your KYS database backup', filetypes=[('KYS database', '*.db')], parent=window)
        if not chosen:
            return
        if Path(chosen).resolve() == live.resolve():
            raise ValueError('Choose a backup or a copy from the old computer, not this running database.')
        # Snapshot selected file once; confirmation applies to these exact contents.
        with tempfile.TemporaryDirectory(prefix='kys-restore-') as temporary:
            staged = Path(temporary) / 'selected.db'
            with closing(connect_readonly(chosen)) as source, closing(sqlite3.connect(str(staged))) as destination:
                source.backup(destination)
            count, latest = inspect_backup(staged, live)
            if not messagebox.askyesno('Confirm restore',
                    'Backup: {}\nTransactions: {}\nLatest transaction: {}\n\n'
                    'This REPLACES current data and user accounts; it does not merge them. '
                    'All staff will be disconnected. A safety copy of current data will be kept. '
                    'After restore, use a username and password from the backup.\n\nRestore now?'.format(Path(chosen).name, count, latest), parent=window):
                return
            with lock.open('x') as handle:
                handle.write(str(os.getpid()))
            locked = True
            powershell = os.path.join(os.environ['SystemRoot'], 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
            restart = True
            result = subprocess.run([powershell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(root / 'Restore Server Control.ps1'), '-Mode', 'Stop', '-WizardPid', str(os.getpid())], capture_output=True, timeout=45, creationflags=0x08000000)
            if result.returncode:
                raise ValueError('Could not stop this server. Restore cancelled. Close the app server and try again.')
            recovery = restore_database(staged, root)
            messagebox.showinfo('Restore complete', 'Data restored successfully. The server will restart when you close this message.\n\nSign in with an account from the backup.\n\nSafety copy: ' + str(recovery), parent=window)
    except Exception as error:
        messagebox.showerror('Restore not completed', str(error), parent=window)
    finally:
        if locked:
            lock.unlink()
        if restart:
            subprocess.Popen([powershell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(root / 'Restore Server Control.ps1'), '-Mode', 'Restart', '-WizardPid', str(os.getpid())], creationflags=0x08000000)
        window.destroy()
