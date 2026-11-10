"""Offline review-kit verifier integration checks.

All cases use generated synthetic fixtures and never execute EXE binaries.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "review-kit" / "generate_samples.py"
VERIFY = ROOT / "review-kit" / "verify_samples.py"


class ReviewKitVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.samples = self.folder / "samples"
        result = self.run_tool(GENERATOR, "--output", str(self.samples))
        self.assertEqual(result.returncode, 0, result.stderr)

    @staticmethod
    def run_tool(script: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(script), *args],
            capture_output=True, text=True, timeout=25, check=False,
        )

    def run_verify(self, *args: str):
        return self.run_tool(VERIFY, "--samples", str(self.samples), *args)

    def test_valid_kit_all_cases_pass_without_independent_claim(self):
        result = self.run_verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["overall_status"], "PASS")
        self.assertEqual(report["case_count"], 9)
        self.assertEqual({case["status"] for case in report["cases"]}, {"PASS"})
        self.assertFalse(report["external_review_verified"])
        self.assertFalse(report["signpath_approved"])
        self.assertFalse(report["existing_unsigned_binaries_verified"])
        self.assertEqual(report["manual_gui_review"], "NOT_PERFORMED")

    def test_report_exposes_no_fixture_secret_paths_or_ip(self):
        result = self.run_verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("DemoOnlyNotReal42", result.stdout)
        self.assertNotIn("DemoQueryShouldHide55", result.stdout)
        self.assertNotIn("198.51.100.12", result.stdout)
        self.assertNotIn(str(self.folder), result.stdout)

    def test_identical_inputs_generate_identical_zip_hashes(self):
        alternate = self.folder / "another"
        result = self.run_tool(GENERATOR, "--output", str(alternate))
        self.assertEqual(result.returncode, 0, result.stderr)
        original = json.loads((self.samples / "manifest.json").read_text(encoding="utf-8"))
        copy = json.loads((alternate / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(original["files_sha256"], copy["files_sha256"])

    def test_changed_fixture_bytes_are_rejected(self):
        (self.samples / "secret-review.env").write_text(
            "database_password=other-fabricated-fixture\n", encoding="utf-8"
        )
        result = self.run_verify()
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCK", result.stderr)
        self.assertNotIn("other-fabricated", result.stderr)

    def test_forged_manifest_does_not_bypass_known_samples(self):
        fixture = self.samples / "plain-review.txt"
        fixture.write_text("altered inert placeholder", encoding="utf-8")
        manifest = self.samples / "manifest.json"
        content = json.loads(manifest.read_text(encoding="utf-8"))
        content["files_sha256"][fixture.name] = hashlib.sha256(fixture.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(content), encoding="utf-8")
        result = self.run_verify()
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCK", result.stderr)

    def test_unexpected_extra_file_is_rejected(self):
        (self.samples / "extra.txt").write_text("not part of the kit", encoding="utf-8")
        result = self.run_verify()
        self.assertEqual(result.returncode, 2)

    def test_report_is_created_once_without_overwrite(self):
        output = self.folder / "review-status.json"
        result = self.run_verify("--report", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["overall_status"], "PASS")
        first = output.read_bytes()
        second = self.run_verify("--report", str(output))
        self.assertEqual(second.returncode, 2)
        self.assertEqual(output.read_bytes(), first)

    def test_refuse_report_inside_sample_directory(self):
        result = self.run_verify("--report", str(self.samples / "results.json"))
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.samples / "results.json").exists())


if __name__ == "__main__":
    unittest.main()
