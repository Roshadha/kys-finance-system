"""Optional company TLS. Invalid configuration fails closed."""
import json
from pathlib import Path
import ssl

def tls_adapter(root):
    settings = Path(root) / 'server-tls.json'
    if not settings.exists():
        return None
    config = json.loads(settings.read_text(encoding='utf-8-sig'))
    cert = Path(config['certificate'])
    key = Path(config['private_key'])
    if not cert.is_absolute():
        cert = Path(root) / cert
    if not key.is_absolute():
        key = Path(root) / key
    from cheroot.ssl.builtin import BuiltinSSLAdapter
    adapter = BuiltinSSLAdapter(str(cert), str(key))
    adapter.context.minimum_version = ssl.TLSVersion.TLSv1_2
    return adapter
