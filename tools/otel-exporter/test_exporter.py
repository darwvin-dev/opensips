#!/usr/bin/env python3
import unittest

import exporter


class ExporterTests(unittest.TestCase):
    def test_metric_name_sanitization(self):
        self.assertEqual(exporter.sanitize_metric_name("dialog:active_dialogs"), "opensips_dialog_active_dialogs")
        self.assertEqual(exporter.sanitize_metric_name("tm:2xx_replies"), "opensips_tm_2xx_replies")

    def test_endpoint_suffix(self):
        self.assertEqual(exporter.otlp_endpoint("http://collector:4318"), "http://collector:4318/v1/metrics")
        self.assertEqual(exporter.otlp_endpoint("http://collector:4318/v1/metrics"), "http://collector:4318/v1/metrics")

    def test_payload_keeps_original_stat_as_attribute(self):
        payload = exporter.build_otlp({"media_qoe:degraded_reports": 7.0}, "opensips-test", "deployment.environment=test", timestamp_ns=123)
        metric = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0]
        self.assertEqual(metric["name"], "opensips_media_qoe_degraded_reports")
        point = metric["gauge"]["dataPoints"][0]
        self.assertEqual(point["timeUnixNano"], "123")
        self.assertEqual(point["attributes"][0]["value"]["stringValue"], "media_qoe:degraded_reports")

    def test_sanitized_metric_name_collisions_get_stable_suffix(self):
        payload = exporter.build_otlp(
            {"custom:a-b": 1.0, "custom:a_b": 2.0},
            "opensips-test", "", timestamp_ns=123,
        )
        metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
        names = [m["name"] for m in metrics]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("opensips_custom_a_b", names)
        self.assertTrue(any(name.startswith("opensips_custom_a_b_") for name in names))

    def test_counter_patterns_emit_cumulative_monotonic_sum(self):
        payload = exporter.build_otlp(
            {"core:received_requests": 42.0, "dialog:active_dialogs": 3.0},
            "opensips-test", "", timestamp_ns=123,
            counter_patterns=["core:*_requests"],
        )
        metrics = {
            m["name"]: m
            for m in payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
        }
        counter = metrics["opensips_core_received_requests"]
        self.assertNotIn("gauge", counter)
        self.assertTrue(counter["sum"]["isMonotonic"])
        self.assertEqual(counter["sum"]["aggregationTemporality"], 2)
        self.assertIn("gauge", metrics["opensips_dialog_active_dialogs"])

    def test_parse_pairs(self):
        self.assertEqual(exporter.parse_pairs("a=1,b=two"), {"a": "1", "b": "two"})
        with self.assertRaises(ValueError):
            exporter.parse_pairs("broken")


if __name__ == "__main__":
    unittest.main()
