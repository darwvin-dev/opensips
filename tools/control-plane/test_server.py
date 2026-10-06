#!/usr/bin/env python3
import unittest

import server


class ControlPlaneTests(unittest.TestCase):
    def test_read_only_classification(self):
        self.assertTrue(server.is_read_only("get_statistics"))
        self.assertTrue(server.is_read_only("show_rtpengines"))
        self.assertTrue(server.is_read_only("status_report:status"))
        self.assertTrue(server.is_read_only("status"))
        self.assertFalse(server.is_read_only("reload"))
        self.assertFalse(server.is_read_only("teardown"))

    def test_listener_safety(self):
        self.assertTrue(server.is_loopback_listener("127.0.0.1"))
        self.assertTrue(server.is_loopback_listener("::1"))
        self.assertTrue(server.is_loopback_listener("localhost"))
        self.assertFalse(server.is_loopback_listener("0.0.0.0"))
        self.assertFalse(server.is_loopback_listener("10.0.0.10"))

    def test_mutations_require_token(self):
        old = server.CONTROL_TOKEN
        try:
            server.CONTROL_TOKEN = "secret"
            self.assertTrue(server.authorized(None, "get_statistics"))
            self.assertFalse(server.authorized(None, "reload"))
            self.assertFalse(server.authorized("Bearer wrong", "reload"))
            self.assertTrue(server.authorized("Bearer secret", "reload"))
        finally:
            server.CONTROL_TOKEN = old

    def test_snapshot_statistics_uses_required_array_param(self):
        old = server.MI

        class FakeMI:
            def call(self, method, params=None):
                return {"method": method, "params": params}

        try:
            server.MI = FakeMI()
            result = server.snapshot_call("get_statistics")
            self.assertEqual(result["params"], {"statistics": ["all"]})
            result = server.snapshot_call("status_report:status")
            self.assertIsNone(result["params"])
        finally:
            server.MI = old

    def test_metrics_prometheus_format(self):
        metrics = server.Metrics()
        metrics.inc_http()
        metrics.observe_mi(12.5, False)
        text = metrics.prometheus()
        self.assertIn("opensips_control_http_requests_total 1", text)
        self.assertIn("opensips_control_mi_requests_total 1", text)
        self.assertIn("opensips_control_mi_last_latency_ms 12.500", text)


if __name__ == "__main__":
    unittest.main()
