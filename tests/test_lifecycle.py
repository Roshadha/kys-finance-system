import threading
import unittest
from lifecycle import DrainGate


class LifecycleTests(unittest.TestCase):
    def test_drain_rejects_new_requests_and_waits_for_existing(self):
        gate = DrainGate(lambda env, start: [b'ok'])
        response = gate({}, lambda *args: None)
        self.assertEqual(gate.active, 1)
        with self.assertRaises(RuntimeError):
            gate.drain(0.01)
        self.assertFalse(gate.draining)
        self.assertEqual(list(response), [b'ok'])
        self.assertEqual(gate.active, 0)
        gate.drain()
        status = []
        self.assertIn(b'Server is stopping', b''.join(gate({}, lambda value, headers: status.append(value))))
        self.assertEqual(status, ['503 Service Unavailable'])

    def test_failed_request_releases_active_count(self):
        def fail(env, start):
            raise ValueError('test')
        gate = DrainGate(fail)
        with self.assertRaises(ValueError):
            list(gate({}, lambda *args: None))
        self.assertEqual(gate.active, 0)
