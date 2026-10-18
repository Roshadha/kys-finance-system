"""Bounded by the parent process; only copies an already verified snapshot."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime


def copy_snapshot(root, snapshot, force=False):
    root, snapshot = Path(root), Path(snapshot)
    target = Path((root / 'backup-target.txt').read_text(encoding='utf-8-sig').strip())
    if not target.is_absolute() or not target.is_dir():
        raise RuntimeError('Configured external backup folder is unavailable.')
    if target.resolve() == root.resolve() or root.resolve() in target.resolve().parents:
        raise RuntimeError('External backup folder must be outside the application folder.')
    stamp = datetime.now()
    day = stamp.strftime('%Y-%m-%d')
    destination = target / 'KYS-Finance-Backups' / (stamp.strftime('%Y-%m-%d_%H%M%S_%f') if force else day)
    manifest_path = destination / 'backup-complete.txt'
    if not force and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if (destination / '.secret_key').exists() and digest(destination / 'kys_finance.db') == manifest['sha256']:
                return destination
        except (ValueError, KeyError, OSError):
            pass
    destination.mkdir(parents=True, exist_ok=True)
    temporary = destination / ('snapshot-{}.tmp'.format(os.getpid()))
    shutil.copy2(str(snapshot), str(temporary))
    with closing(sqlite3.connect(str(temporary))) as connection:
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('External backup integrity check failed.')
    checksum = digest(temporary)
    temporary.replace(destination / 'kys_finance.db')
    secret = root / 'data' / '.secret_key'
    secret_temp = destination / ('.secret-key-{}.tmp'.format(os.getpid()))
    if os.environ.get('KYS_SECRET_KEY'):
        secret_temp.write_text(os.environ['KYS_SECRET_KEY'], encoding='utf-8')
    elif secret.exists():
        shutil.copy2(str(secret), str(secret_temp))
    else:
        raise RuntimeError('Session secret is unavailable.')
    secret_temp.replace(destination / '.secret_key')
    marker = destination / ('manifest-{}.tmp'.format(os.getpid()))
    marker.write_text(json.dumps({'sha256': checksum, 'verified_at': stamp.isoformat()}), encoding='utf-8')
    marker.replace(manifest_path)
    return destination


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main(arguments):
    try:
        print(json.dumps({'path': str(copy_snapshot(arguments[0], arguments[1], arguments[2] == '1'))}))
        return 0
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
