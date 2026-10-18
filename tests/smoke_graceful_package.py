"""Disposable packaged Windows server, network request, and desktop stop path."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[1]
source = root / 'release/company-win7/KYS Finance Server'
with tempfile.TemporaryDirectory(prefix='stop-smoke-', dir=str(root / 'tmp')) as temporary:
    target = Path(temporary) / 'server'
    shutil.copytree(str(source), str(target))
    exe = target / 'KYS Finance Server.exe'
    environment = {k: v for k, v in os.environ.items() if not k.startswith('KYS_') and k != 'PORT'}
    environment['KYS_HOST'] = '127.0.0.1'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    environment['PORT'] = str(port)
    setup = subprocess.run([str(exe), '--configure-admin-json'], cwd=str(target), env=environment,
        input=json.dumps({'username': 'test-owner', 'password': 'TestOnly123!'}), text=True,
        capture_output=True, timeout=90)
    assert setup.returncode == 0, setup.stderr
    server = subprocess.Popen([str(exe)], cwd=str(target), env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        last_connection_error = None
        for _ in range(120):
            if server.poll() is not None:
                raise AssertionError('Packaged server exited before health check')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1) as connection:
                    connection.sendall(b'GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n')
                    connection.settimeout(1)
                    assert b'200 OK' in connection.recv(4096)
                break
            except OSError as error:
                last_connection_error = repr(error)
                time.sleep(0.25)
        else:
            details = (target / 'server-error.log').read_text(encoding='utf-8', errors='replace') if (target / 'server-error.log').exists() else 'no server-error.log'
            startup = (target / 'server-startup.log').read_text(encoding='utf-8', errors='replace') if (target / 'server-startup.log').exists() else 'no server-startup.log'
            raise AssertionError('Packaged server did not become ready; pid={} port={}; connect={}; error={}; startup={}'.format(server.pid, port, last_connection_error, details[-2000:], startup[-2000:]))
        powershell = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        stop = subprocess.run([str(powershell), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            str(target / 'Stop Company Server.ps1'), '-NoConfirm'], cwd=str(target),
            text=True, capture_output=True, timeout=125)
        assert stop.returncode == 0, stop.stderr
        assert server.wait(timeout=5) == 0
        assert list((target / 'backups').glob('kys_finance_*.db'))
        print('PASS: packaged server responds, Stop shortcut script drains, backs up and exits')
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=10)
