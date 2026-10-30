"""Offline fail-closed checks for the optional AI advisory JSON boundary."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from safe_analysis_input import parse_strict_json, to_advisory_packet


class StrictAdvisoryJSONTests(unittest.TestCase):
    @staticmethod
    def valid_report():
        keys = (
            "raw_ip_exported", "node_ids_exported", "raw_ua_exported",
            "raw_path_exported", "raw_headers_exported", "small_counts_suppressed",
        )
        return {
            "schema": "trapnet.public-aggregate.v1",
            "classification": "unverified_observation_not_attack",
            "small_cohorts_omitted": True,
            "privacy": {k: (k == "small_counts_suppressed") for k in keys},
            "observations_band": "10-49",
            "path_category_bands": {"api": "10-49"},
            "status_family_bands": {"4xx": "10-49"},
        }

    def test_valid_packet_unchanged_and_advisory_only(self):
        raw = json.dumps(self.valid_report())
        parsed = parse_strict_json(raw)
        self.assertEqual(parsed, self.valid_report())
        packet = to_advisory_packet(parsed)
        self.assertEqual(packet["allowed_actions"], [])
        self.assertIs(packet["can_execute_commands"], False)
        self.assertIs(packet["can_trigger_blocking"], False)
        self.assertIs(packet["requires_human_review"], True)

    def test_duplicate_top_level_schema_rejected(self):
        raw = json.dumps(self.valid_report())
        raw = raw.replace('"schema": ', '"schema": "forged", "schema": ', 1)
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_strict_json(raw)

    def test_duplicate_nested_privacy_flag_rejected(self):
        raw = json.dumps(self.valid_report())
        raw = raw.replace('"raw_ip_exported": false',
                          '"raw_ip_exported": true, "raw_ip_exported": false', 1)
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_strict_json(raw)

    def test_escaped_alias_duplicate_key_rejected(self):
        raw = r'{"path_category_bands":{"api": "10-49", "\u0061pi": "10-49"}}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_strict_json(raw)

    def test_repeated_values_are_not_duplicate_keys(self):
        self.assertEqual(parse_strict_json('{"a":[1,1],"b":1}'),
                         {"a": [1, 1], "b": 1})

    def test_cli_rejects_ambiguous_json_without_echo(self):
        raw = json.dumps(self.valid_report())
        raw = raw.replace('"schema": ',
                          '"schema": "ATTACKER_CONTENT", "schema": ', 1)
        with tempfile.TemporaryDirectory() as root:
            source = pathlib.Path(root) / "report.json"
            source.write_text(raw, encoding="utf-8")
            script = pathlib.Path(__file__).with_name("safe_analysis_input.py")
            run = subprocess.run(
                [sys.executable, str(script), "--input", str(source)],
                capture_output=True, text=True, timeout=20, check=False,
            )
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual(json.loads(run.stdout),
                         {"accepted": False, "error_class": "ValueError"})
        self.assertNotIn("ATTACKER_CONTENT", run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
