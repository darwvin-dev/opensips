#!/usr/bin/env python3
import unittest

import impair


class ImpairTests(unittest.TestCase):
    def test_bad_mobile_command(self):
        cmd = impair.build_apply("eth0", impair.PROFILES["bad-mobile"])
        self.assertEqual(cmd[:6], ["tc", "qdisc", "replace", "dev", "eth0", "root"])
        joined = " ".join(cmd)
        self.assertIn("delay 160ms 80ms distribution normal", joined)
        self.assertIn("loss random 7%", joined)
        self.assertIn("reorder 2% 50%", joined)
        self.assertIn("rate 900kbit", joined)

    def test_burst_loss_is_correlated(self):
        cmd = impair.build_apply("eth0", impair.PROFILES["burst-loss"])
        self.assertIn("loss random 12% 70%", " ".join(cmd))

    def test_loss_correlation_requires_loss(self):
        with self.assertRaises(ValueError):
            impair.validate_profile(impair.Profile(loss_correlation_pct=50))

    def test_namespace_prefix(self):
        cmd = impair.build_show("veth-media", "media-test")
        self.assertEqual(cmd[:5], ["ip", "netns", "exec", "media-test", "tc"])

    def test_rejects_unsafe_interface(self):
        with self.assertRaises(ValueError):
            impair.build_clear("eth0;rm -rf /")

    def test_rejects_invalid_percentage(self):
        with self.assertRaises(ValueError):
            impair.validate_profile(impair.Profile(loss_pct=101))

    def test_reorder_requires_delay(self):
        with self.assertRaises(ValueError):
            impair.validate_profile(impair.Profile(reorder_pct=1))


if __name__ == "__main__":
    unittest.main()
