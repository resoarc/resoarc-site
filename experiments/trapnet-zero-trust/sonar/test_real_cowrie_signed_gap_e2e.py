#!/usr/bin/env python3
"""Safe static and fail-closed checks for the privileged Cowrie E2E CI lab."""
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"lab"))
import real_cowrie_signed_gap_e2e as actual
import cowrie_ext4_persistent_rehearsal as ext4

class RealCowrieGapE2ESafety(unittest.TestCase):
    def test_pinned_repository_digest(self):
        self.assertTrue(actual.IMAGE_REF.startswith("cowrie/cowrie@sha256:"))
        self.assertEqual(len(actual.IMAGE_REF.split("sha256:")[-1]),64)
        self.assertEqual(actual.IMAGE_ID,ext4.IMAGE_DEFAULT)
    def test_does_not_use_live_production_image_or_paths(self):
        body=(ROOT/"lab"/"real_cowrie_signed_gap_e2e.py").read_text(encoding="utf-8")
        self.assertIn('tempfile.TemporaryDirectory(prefix="trapnet-real-cowrie-gap-v047-"',body)
        self.assertIn("production_modified",body)
        self.assertIn('no_public_ports":True',body)
    def test_docker_cowrie_is_networkless_and_readonly(self):
        body=(ROOT/"sonar"/"cowrie_ext4_persistent_rehearsal.py").read_text(encoding="utf-8")
        self.assertIn('"--network","none"',body)
        self.assertIn('"--read-only"',body)
        self.assertIn('"--cap-drop","ALL"',body)
        self.assertIn('loop,nosuid,nodev,noexec',body)
    def test_wrong_image_refused_before_docker_or_mount(self):
        with patch.object(actual.sys,"platform","linux"):
            with patch.object(actual.os,"geteuid",return_value=0,create=True):
                with patch.object(actual.ext4,"image_verified") as inspect:
                    with self.assertRaises(ValueError):
                        actual.exercise("cowrie/cowrie:latest")
                    inspect.assert_not_called()
    def test_failure_and_recovery_hooks_are_required(self):
        body=(ROOT/"sonar"/"cowrie_ext4_persistent_rehearsal.py").read_text(encoding="utf-8")
        self.assertIn('failure_hook(root,mountpoint,report) is True',body)
        self.assertIn('recovery_hook(root,mountpoint,report) is True',body)
        self.assertIn('report.get("signed_gap_failure_hook",False)',body)
        self.assertIn('report.get("signed_gap_recovery_hook",False)',body)
    def test_lost_or_expired_coverage_is_never_implicitly_cleared(self):
        body=(ROOT/"lab"/"real_cowrie_signed_gap_e2e.py").read_text(encoding="utf-8")
        self.assertIn('"recovered_real_log_parseable_without_auto_clear"',body)
        self.assertIn('"historical_gap_not_automatically_erased"',body)
    def test_output_does_not_expose_keys_or_raw_events(self):
        body=(ROOT/"lab"/"real_cowrie_signed_gap_e2e.py").read_text(encoding="utf-8")
        self.assertIn('"raw_events_exported":False',body)
        self.assertIn('"private_keys_exported":False',body)
        self.assertNotIn('print(data)',body)

if __name__=="__main__":unittest.main()
