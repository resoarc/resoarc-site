#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Guard against accidental promotion of an unsigned operational outage."""
import datetime
import json
from pathlib import Path
import unittest

EVIDENCE = Path(__file__).with_name("live_gap_20261105_v062.json")


class LiveGapEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_public_release_always_hold_for_unsigned_gap(self):
        self.assertEqual(self.record["public_release"], "HOLD")
        self.assertFalse(self.record["signed_sensor_gap_report"])
        self.assertFalse(self.record["independent_witness_ack"])
        self.assertEqual(self.record["formal_gate_updates"], [])

    def test_no_zero_attack_claim(self):
        self.assertFalse(self.record["claim_zero_attacks"])
        self.assertIsNone(self.record["reported_attacks_during_gap"])

    def test_gap_interval_timezone_valid_and_positive(self):
        begin = datetime.datetime.fromisoformat(self.record["gap_start_utc"].replace("Z", "+00:00"))
        end = datetime.datetime.fromisoformat(self.record["gap_end_utc"].replace("Z", "+00:00"))
        self.assertGreater(end, begin)
        self.assertGreater((end - begin).total_seconds(), 60 * 60 * 12)

    def test_gate_impact_not_hidden(self):
        self.assertTrue({"A3", "B2", "E1", "E3"}.issubset(self.record["remaining_gates"]))
        self.assertFalse(self.record["deployment_v062"]["external_human_review"])

    def test_no_raw_log_content_or_ip_addresses(self):
        raw = EVIDENCE.read_text(encoding="utf-8")
        self.assertNotIn("password", raw.lower())
        self.assertNotIn("src_ip", raw.lower())
        self.assertNotIn("private_key", raw.lower())


if __name__ == "__main__":
    unittest.main()
