"""Local-file shutdown control; no unauthenticated HTTP shutdown endpoint."""
import json
import os
from pathlib import Path
import threading
import time


class DrainGate:
    def __init__(self, application):
        self.application = application
        self.condition = threading.Condition()
        self.active = 0
        self.draining = False

    def __call__(self, environ, start_response):
        with self.condition:
            if self.draining:
                start_response('503 Service Unavailable', [('Content-Type', 'text/plain'), ('Retry-After', '30')])
                return [b'Server is stopping. Please wait; do not repeat a save until you check the ledger.']
            self.active += 1
        released = False
        def release():
            nonlocal released
            with self.condition:
                if not released:
                    released = True
                    self.active -= 1
                    self.condition.notify_all()
        def response():
            iterable = None
            try:
                iterable = self.application(environ, start_response)
                yield from iterable
            finally:
                try:
                    if hasattr(iterable, 'close'):
                        iterable.close()
                finally:
                    release()
        iterator = response()
        class Response:
            def __iter__(self):
                return iterator
            def close(self):
                try:
                    iterator.close()
                finally:
                    release()
        return Response()

    def drain(self, timeout=30):
        deadline = time.monotonic() + timeout
        with self.condition:
            self.draining = True
            while self.active:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.draining = False
                    raise RuntimeError('Requests are still running. Stop cancelled; finish work and retry.')
                self.condition.wait(remaining)

    def resume(self):
        with self.condition:
            self.draining = False


def monitor_shutdown(application, gate, root, backup, stop):
    root = Path(root)
    request = root / 'shutdown.request'
    result = root / 'shutdown-result.json'
    request.unlink(missing_ok=True)  # Never replay an old stop request on restart.
    stopped = threading.Event()
    def worker():
        while not stopped.wait(0.25):
            if not request.exists():
                continue
            try:
                nonce = request.read_text(encoding='utf-8-sig').strip()
                request.unlink()
                gate.drain(30)
                backup(application, local_only=True)
                result.write_text(json.dumps({'request': nonce, 'status': 'stopping'}), encoding='utf-8')
                stop()
                return
            except Exception as error:
                gate.resume()
                application.logger.exception('Graceful shutdown cancelled')
                result.write_text(json.dumps({'status': 'failed', 'error': str(error)}), encoding='utf-8')
    threading.Thread(target=worker, daemon=True, name='graceful-stop').start()
    return stopped


def prevent_sleep(enabled):
    if os.name == 'nt' and os.environ.get('KYS_ALLOW_SLEEP') != '1':
        import ctypes
        return ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 if enabled else 0x80000000)
