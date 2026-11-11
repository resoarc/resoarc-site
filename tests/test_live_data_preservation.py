#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Offline acceptance tests for the fail-closed public snapshot guard."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_live_data_preservation.py"
SPEC = importlib.util.spec_from_file_location("verify_live_data_preservation", MODULE_PATH)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class LiveDataPreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name)
        self.snapshots = {}
        for path in guard.SNAPSHOT_FILES:
            content = ("snapshot:" + path).encode("utf-8")
            self.snapshots[path] = content
            target = self.site / path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def test_exact_bytes_pass(self):
        success, problems = guard.check(lambda p: self.snapshots[p], self.site)
        self.assertTrue(success)
        self.assertEqual(problems, [])

    def test_any_changed_snapshot_blocks(self):
        changed = dict(self.snapshots)
        changed[guard.SNAPSHOT_FILES[1]] += b"new-content"
        success, problems = guard.check(lambda p: changed[p], self.site)
        self.assertFalse(success)
        self.assertEqual(len(problems), 1)
        self.assertIn(guard.SNAPSHOT_FILES[1], problems[0])

    def test_missing_candidate_blocks(self):
        target = self.site / guard.SNAPSHOT_FILES[0].lstrip("/")
        target.unlink()
        success, problems = guard.check(lambda p: self.snapshots[p], self.site)
        self.assertFalse(success)
        self.assertIn("missing candidate", problems[0])

    def test_network_failure_blocks(self):
        def raise_error(path):
            raise TimeoutError("unavailable")
        success, problems = guard.check(raise_error, self.site)
        self.assertFalse(success)
        self.assertEqual(len(problems), len(guard.SNAPSHOT_FILES))

    def test_oversized_live_content_blocks(self):
        huge = b"x" * (guard.MAX_BYTES + 1)
        success, problems = guard.check(
            lambda p: huge if p == guard.SNAPSHOT_FILES[0] else self.snapshots[p],
            self.site,
        )
        self.assertFalse(success)
        self.assertEqual(len(problems), 1)
        self.assertIn("size limit", problems[0])

    def test_oversized_candidate_blocks_without_fetch(self):
        path = guard.SNAPSHOT_FILES[2]
        (self.site / path.lstrip("/")).write_bytes(b"z" * (guard.MAX_BYTES + 1))
        called = []
        def record_fetch(p):
            called.append(p)
            return self.snapshots[p]
        success, problems = guard.check(record_fetch, self.site)
        self.assertFalse(success)
        self.assertIn(path, problems[0])
        self.assertNotIn(path, called)


if __name__ == "__main__":
    unittest.main()
