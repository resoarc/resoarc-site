#!/usr/bin/env python3
"""No-network unit checks for the manual ext4 rehearsal. CI never mounts disks."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cowrie_ext4_persistent_rehearsal as lab

class Ext4RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"cowrie.json"
    def write(self,events):
        self.path.write_bytes(events)
        return self.path
    def test_fixture_with_valid_event(self):
        data=b'{"eventid":"cowrie.session.connect"}\n'
        self.write(data)
        body,count=lab.log_snapshot(self.path)
        self.assertEqual(body,data)
        self.assertEqual(count,1)
    def test_multiple_events(self):
        self.write(b'{"eventid":"one"}\n{"eventid":"two"}\n')
        self.assertEqual(lab.log_snapshot(self.path)[1],2)
    def test_missing_log_refused(self):
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_empty_log_refused(self):
        self.write(b"")
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_partial_tail_refused(self):
        self.write(b'{"eventid":"one"}')
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_invalid_json_refused(self):
        self.write(b'{"eventid":}\n')
        with self.assertRaises(ValueError):lab.log_snapshot(self.path)
    def test_nonobject_json_refused(self):
        self.write(b'[1,2]\n')
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_missing_eventid_refused(self):
        self.write(b'{"src_ip":"198.51.100.1"}\n')
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_nonstring_eventid_refused(self):
        self.write(b'{"eventid":12}\n')
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_large_log_refused(self):
        self.write(b'{"eventid":"'+b"x"*(2*1024*1024)+b'"}\n')
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_symlink_refused(self):
        source=self.path.parent/"safe.json"
        source.write_bytes(b'{"eventid":"ok"}\n')
        try:self.path.symlink_to(source)
        except OSError:self.skipTest("symlink unsupported")
        with self.assertRaises(RuntimeError):lab.log_snapshot(self.path)
    def test_immutable_image_required_before_root_or_file_ops(self):
        with patch.object(lab,"image_verified",side_effect=ValueError("invalid image")):
            with self.assertRaises(ValueError):
                lab.trial("cowrie:latest",self.tmp.name)
        self.assertEqual(sorted(p.name for p in Path(self.tmp.name).iterdir()),[])
    def test_no_custom_network_or_host_port(self):
        source=Path(lab.__file__).read_text(encoding="utf-8")
        self.assertIn('"--network","none"',source)
        self.assertIn('"--read-only"',source)
        self.assertIn('"--cap-drop","ALL"',source)
        self.assertNotIn('"--publish"',source)
        self.assertNotIn('"--privileged"',source)
    def test_quota_is_ext4_not_unbounded_host_bind(self):
        source=Path(lab.__file__).read_text(encoding="utf-8")
        self.assertIn('"mkfs.ext4"',source)
        self.assertIn('loop,nosuid,nodev,noexec',source)
        self.assertIn('"VOLUME_LIMIT_NOT_PROVEN"',Path(__file__).with_name("cowrie_log_health.py").read_text(encoding="utf-8"))
    def test_rehearsal_never_implies_release_approved(self):
        self.assertEqual(lab.CAPACITY,16777216)
        source=Path(lab.__file__).read_text(encoding="utf-8")
        self.assertIn('"release_approved":False',source)

if __name__=="__main__":
    unittest.main()
