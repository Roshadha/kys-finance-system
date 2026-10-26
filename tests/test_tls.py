import json
import os
import shutil
import ssl
import subprocess
import tempfile
import threading
from pathlib import Path
from unittest import TestCase
from urllib.request import urlopen
from cheroot.wsgi import Server
from server_security import tls_adapter

class TLSTests(TestCase):
    def test_unconfigured_tls_and_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertIsNone(tls_adapter(root))
            (root/'server-tls.json').write_text(json.dumps({'certificate':'missing.pem','private_key':'missing.key'}))
            with self.assertRaises((OSError,ValueError)):
                tls_adapter(root)

    def test_verified_tls_connection_requires_correct_hostname(self):
        openssl=shutil.which('openssl') or r'C:\Program Files\Git\mingw64\bin\openssl.exe'
        if not Path(openssl).exists():
            self.skipTest('OpenSSL executable required for ephemeral TLS test certificate')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'openssl.cnf').write_text('[req]\ndistinguished_name=dn\n[dn]\n')
            subprocess.run([openssl,'req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                '-config',str(root/'openssl.cnf'),
                '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost',
                '-keyout',str(root/'key.pem'),'-out',str(root/'cert.pem')],check=True,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            (root/'server-tls.json').write_text(json.dumps({'certificate':'cert.pem','private_key':'key.pem'}))
            adapter=tls_adapter(root)
            self.assertEqual(adapter.context.minimum_version,ssl.TLSVersion.TLSv1_2)
            def application(environ,start_response):
                start_response('200 OK',[('Content-Type','text/plain')]);return [b'verified']
            server=Server(('127.0.0.1',0),application)
            server.ssl_adapter=adapter
            server.prepare()
            thread=threading.Thread(target=server.serve,daemon=True);thread.start()
            try:
                context=ssl.create_default_context(cafile=str(root/'cert.pem'))
                with urlopen('https://localhost:%s/' % server.bind_addr[1],context=context,timeout=5) as response:
                    self.assertEqual(response.read(),b'verified')
                with self.assertRaises(Exception):
                    urlopen('https://127.0.0.1:%s/' % server.bind_addr[1],context=context,timeout=5)
            finally:
                server.stop();thread.join(timeout=5)

