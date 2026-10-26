"""Persistent backup preferences and administrator-visible results."""
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MINUTES = 15

def read_settings(root):
    try:
        value = int(json.loads((Path(root) / 'backup-settings.json').read_text())['interval_minutes'])
        if 5 <= value <= 1440:
            return {'interval_minutes': value}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {'interval_minutes': DEFAULT_MINUTES}

def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.replace(path)

def save_settings(root, minutes):
    minutes = int(minutes)
    if not 5 <= minutes <= 1440:
        raise ValueError('Choose an interval between 5 and 1440 minutes.')
    atomic_json(Path(root) / 'backup-settings.json', {'interval_minutes': minutes})

def read_status(root):
    try:
        return json.loads((Path(root) / 'backup-status.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}

def record_status(root, local=None, external=None, error=None, local_error=None, external_attempted=True):
    status = read_status(root)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    status['last_attempt'] = now
    if local:
        status['last_local'] = now
        status['local_file'] = Path(local).name
    if external:
        status['last_external'] = now
    if external_attempted:
        status['external_error'] = error
    status['local_error'] = local_error
    atomic_json(Path(root) / 'backup-status.json', status)
