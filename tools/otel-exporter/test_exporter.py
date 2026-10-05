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

    def test_parse_pairs(self):
        self.assertEqual(exporter.parse_pairs("a=1,b=two"), {"a": "1", "b": "two"})
        with self.assertRaises(ValueError):
            exporter.parse_pairs("broken")


if __name__ == "__main__":
    unittest.main()
