"""Record the exact application inputs used by the Windows release build."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from release_info import VERSION, SCHEMA_VERSION

root = Path(__file__).resolve().parent
paths = [p for p in root.glob('*.py') if p.name != 'audit_probe.py']
for directory in ('templates', 'static', 'legacy', 'client', 'assets'):
    paths.extend(p for p in (root / directory).rglob('*')
                 if p.is_file() and p.suffix.lower() in {'.py', '.html', '.js', '.css', '.ps1', '.cmd', '.ico', '.png'})
hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(paths)}
commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
dirty = bool(subprocess.check_output(['git','diff','HEAD','--name-only'], cwd=root, text=True).strip())
info = {'version':VERSION, 'schema_version':SCHEMA_VERSION, 'commit':commit,
        'uncommitted_changes':dirty, 'built_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':hashes}
destination = root / 'build-package' / 'build-info.json'
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps(info, indent=2), encoding='utf-8')
print('Build metadata:', destination)
