"""Contract checks for the public, synthetic-only reviewer kit.

Tests verify actual Security Trio scanners against the generated mock inputs.
Internal maintainer tests are NOT counted as independent third-party reviews.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import file_inspector
import log_lantern
import secret_scout

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "review-kit" / "generate_samples.py"


class ExternalReviewKitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.out = self.root / "generated"
        self.proc = subprocess.run(
            [sys.executable, "-B", str(GENERATOR), "--output", str(self.out)],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))

    def test_exact_files_and_hashes(self):
        self.assertEqual(self.manifest["type"], "SYNTHETIC_LOCAL_REVIEW_ONLY")
        self.assertEqual(len(self.manifest["files_sha256"]), 9)
        names = set(self.manifest["files_sha256"])
        self.assertEqual({p.name for p in self.out.iterdir()}, names | {"manifest.json"})
        for name, expected in self.manifest["files_sha256"].items():
            self.assertEqual(hashlib.sha256((self.out / name).read_bytes()).hexdigest(), expected)
        self.assertFalse((self.root / "escape.txt").exists())

    def test_refuse_overwriting_generated_samples(self):
        second = subprocess.run(
            [sys.executable, "-B", str(GENERATOR), "--output", str(self.out)],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("BLOCK", second.stderr)

    def test_secret_scout_mock_and_placeholder(self):
        result = secret_scout.scan([self.out / "secret-review.env"])
        self.assertTrue(any(f.rule == "機密値を含む設定" for f in result.findings))
        self.assertNotIn("DemoOnlyNotReal42", json.dumps(result.export_data(), ensure_ascii=False))
        clean = secret_scout.scan([self.out / "secret-placeholder.env"])
        self.assertFalse(clean.findings)

    def test_zip_secret_and_non_extraction(self):
        result = secret_scout.scan([self.out / "archive-review.zip"])
        rules = [f.rule for f in result.findings]
        self.assertIn("機密値を含む設定", rules)
        self.assertIn("ZIP内の危険なパス", rules)
        self.assertFalse((self.root / "escape.txt").exists())

    def test_log_findings_and_redaction(self):
        result = log_lantern.scan([self.out / "access-review.log"])
        self.assertEqual(result.metrics["requests"], 15)
        rules = [f.rule for f in result.findings]
        self.assertTrue(any("秘密" in rule for rule in rules), rules)
        self.assertTrue(any("404" in rule for rule in rules), rules)
        data = json.dumps(result.export_data(), ensure_ascii=False)
        self.assertNotIn("DemoQueryShouldHide55", data)
        self.assertNotIn("198.51.100.12", data)
        normal = log_lantern.scan([self.out / "normal-access.log"])
        self.assertEqual(normal.metrics["requests"], 1)
        self.assertFalse(normal.findings)

    def test_file_inspector_static_patterns(self):
        warning = file_inspector.scan([self.out / "pdf-marker-review.pdf"])
        self.assertTrue(any("PDF" in f.rule for f in warning.findings))
        mismatch = file_inspector.scan([self.out / "mismatch-review.pdf"])
        self.assertTrue(any("不一致" in f.rule for f in mismatch.findings))
        double = file_inspector.scan([self.out / "double-extension.pdf.exe"])
        self.assertTrue(any("二重" in f.rule for f in double.findings))
        harmless = file_inspector.scan([self.out / "plain-review.txt"])
        self.assertFalse(harmless.findings)


if __name__ == "__main__":
    unittest.main()
