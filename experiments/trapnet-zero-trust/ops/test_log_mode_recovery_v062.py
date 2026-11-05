#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline, synthetic acceptance checks for least-privilege Cowrie log recovery."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

FILE = Path(__file__).resolve().parent / "log_mode_recovery_v062.py"
spec = importlib.util.spec_from_file_location("log_mode_recovery_v062", FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PolicyTests(unittest.TestCase):
    def test_active_mode_0664_authorized(self):
        self.assertTrue(m.authorize_active_repair("cowrie.json", 0o664, 999, 1, True, 999))

    def test_other_filename_cannot_be_repaired(self):
        for name in ("cowrie.json.2026-11-05", "cowrie.log", "../cowrie.json", "cowrie.json/"):
            with self.subTest(name=name):
                self.assertFalse(m.authorize_active_repair(name, 0o664, 999, 1, True, 999))

    def test_other_modes_never_auto_repaired(self):
        for mode in (0, 0o777, 0o666, 0o644, 0o600, 0o400, True, None):
            with self.subTest(mode=mode):
                self.assertFalse(m.authorize_active_repair("cowrie.json", mode, 999, 1, True, 999))

    def test_other_owner_or_hardlinks_rejected(self):
        for uid, nlink, ordinary in ((0, 1, True), (998, 1, True),
                                     (999, 2, True), (999, 1, False)):
            self.assertFalse(m.authorize_active_repair("cowrie.json", 0o664, uid,
                                                      nlink, ordinary, 999))

    def test_bounded_mount_refuses_regular_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(m.UnsafeMetadata):
                m.verify_bounded_mount(Path(tmp))

    def test_output_schema_never_advertises_release(self):
        self.assertEqual(m.SCHEMA, "trapnet.cowrie.log-mode-recovery.v062")
        self.assertEqual(m.EXPECTED_UID, 999)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_dry_run_then_exact_mode_repair(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "log"
            logs.mkdir(mode=0o700)
            f = logs / "cowrie.json"
            f.write_text("synthetic only")
            f.chmod(0o664)
            v = m.inspect_and_normalize(logs, os.getuid(), False)
            self.assertEqual((v["checked"], v["repairable"], v["repaired"]), (1, 1, 0))
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o664)
            v = m.inspect_and_normalize(logs, os.getuid(), True)
            self.assertEqual(v["repaired"], 1)
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
            self.assertEqual(m.inspect_and_normalize(logs, os.getuid(), True)["repaired"], 0)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_unknown_mode_fail_closed_without_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "log"
            logs.mkdir(mode=0o700)
            f = logs / "cowrie.json"
            f.write_text("synthetic only")
            f.chmod(0o777)
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(logs, os.getuid(), True)
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o777)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_hardlinked_file_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "log"
            logs.mkdir(mode=0o700)
            f = logs / "cowrie.json"
            f.write_text("synthetic only")
            f.chmod(0o664)
            os.link(f, Path(root) / "other")
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(logs, os.getuid(), True)
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o664)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_symlinked_log_file_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "log"
            logs.mkdir(mode=0o700)
            f = Path(root) / "target"
            f.write_text("synthetic only")
            f.chmod(0o664)
            (logs / "cowrie.json").symlink_to(f)
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(logs, os.getuid(), True)
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o664)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_symlinked_log_directory_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "real"
            logs.mkdir(mode=0o700)
            (logs / "cowrie.json").write_text("synthetic only")
            (Path(root) / "link").symlink_to(logs)
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(Path(root) / "link", os.getuid(), True)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_mode_0700_and_owner_required(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "log"
            logs.mkdir(mode=0o700)
            (logs / "cowrie.json").write_text("synthetic only")
            logs.chmod(0o750)
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(logs, os.getuid(), True)
            logs.chmod(0o700)
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(logs, os.getuid() + 1, True)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_rotated_log_mode_not_silently_fixed(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "log"
            logs.mkdir(mode=0o700)
            active = logs / "cowrie.json"
            active.write_text("synthetic only")
            active.chmod(0o600)
            rotated = logs / "cowrie.json.2026-11-04"
            rotated.write_text("synthetic only")
            rotated.chmod(0o664)
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(logs, os.getuid(), True)
            self.assertEqual(stat.S_IMODE(rotated.stat().st_mode), 0o664)

    @unittest.skipUnless(os.name == "posix", "POSIX uid/mode and fchmod required")
    def test_missing_logs_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / "log"
            logs.mkdir(mode=0o700)
            with self.assertRaises(m.UnsafeMetadata):
                m.inspect_and_normalize(logs, os.getuid(), False)


if __name__ == "__main__":
    unittest.main()
