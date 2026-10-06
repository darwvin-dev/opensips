#!/usr/bin/env python3
import argparse
import tempfile
import unittest
from pathlib import Path

import sipp_report


SAMPLE = """StartTime;SuccessfulCall(C);FailedCall(C);ResponseTime1(C);CallRate(C)\n0;95;5;00:00:00:120000;50\n1;198;2;00:00:00:085000;75\n"""


class SippReportTests(unittest.TestCase):
    def test_summary_uses_final_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stats.csv"
            path.write_text(SAMPLE, encoding="utf-8")
            summary = sipp_report.summarize(sipp_report.load_final_row(path))
        self.assertEqual(summary["successful_calls"], 198)
        self.assertEqual(summary["failed_calls"], 2)
        self.assertEqual(summary["response_time_ms"], 85)
        self.assertAlmostEqual(summary["success_rate"], 99.0)

    def test_response_time_duration_is_converted_to_ms(self):
        self.assertEqual(sipp_report._duration_ms("00:00:00:002000"), 2.0)
        self.assertEqual(sipp_report._duration_ms("00:00:01:500000"), 1500.0)
        self.assertEqual(sipp_report._duration_ms("00:01:00"), 60000.0)
        self.assertIsNone(sipp_report._duration_ms("not-a-time"))

    def test_threshold_failure(self):
        summary = {
            "successful_calls": 90,
            "failed_calls": 10,
            "response_time_ms": 250,
            "call_rate": 25,
            "success_rate": 90,
        }
        args = argparse.Namespace(
            min_successful_calls=100,
            max_failed_calls=0,
            min_success_rate=99.5,
            max_response_time_ms=100,
            min_call_rate=50,
        )
        checks = sipp_report.evaluate(summary, args)
        self.assertEqual(len(checks), 5)
        self.assertTrue(all(not passed for _, passed, _ in checks))


if __name__ == "__main__":
    unittest.main()
