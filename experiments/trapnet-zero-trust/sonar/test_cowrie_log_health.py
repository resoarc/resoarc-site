import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import cowrie_log_health as guard

def stat(free=4*1024*1024,capacity=8*1024*1024):
    return SimpleNamespace(f_blocks=capacity//4096,f_frsize=4096,f_bavail=free//4096)

class TestCowrieLogHealth(unittest.TestCase):
    def fixture(self,d):
        root=Path(d)
        path=root/"log/cowrie/cowrie.json";path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"eventid":"cowrie.session.connect","src_ip":"PRIVATE"})+"\n")
        return root,path
    def assess_with(self,root,free=4*1024*1024,capacity=8*1024*1024):
        with patch.object(guard.os,"statvfs",return_value=stat(free,capacity)):
            return guard.assess(root)
    def test_healthy_bounded_private_log(self):
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            res=self.assess_with(root)
            self.assertTrue(res["passed"])
            self.assertEqual(res["log_entries"],1)
            self.assertNotIn("PRIVATE",json.dumps(res))
            self.assertFalse(res["public_beta_ready"])
            self.assertFalse(res["new_event_append_proven"])
    def test_full_volume_rejected_even_if_log_parseable(self):
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            res=self.assess_with(root,free=0)
            self.assertFalse(res["passed"])
            self.assertIn("FREE_SPACE_LOW",res["issues"])
    def test_unbounded_filesystem_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            self.assertIn("VOLUME_LIMIT_NOT_PROVEN",self.assess_with(root,capacity=128*1024*1024)["issues"])
    def test_missing_or_invalid_log(self):
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d);path.unlink()
            self.assertIn("JSON_LOG_MISSING",self.assess_with(root)["issues"])
            path.write_bytes(b"NOTJSON\n")
            self.assertIn("JSON_LINE_INVALID",self.assess_with(root)["issues"])
    def test_no_newline_and_invalid_structure_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d);path.write_bytes(b'{"eventid":"cowrie.session.connect"}')
            self.assertIn("JSON_LINE_INVALID",self.assess_with(root)["issues"])
            path.write_bytes(b'{"src_ip":"SECRET"}\n')
            self.assertIn("JSON_EVENT_INVALID",self.assess_with(root)["issues"])
    def test_symlink_path_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d)
            original=root/"other.json";path.rename(original)
            try:path.symlink_to(original)
            except OSError:self.skipTest("symlink unavailable")
            self.assertIn("LOG_PATH_SYMLINK",self.assess_with(root)["issues"])
    def test_invalid_thresholds_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            self.assertIn("INVALID_THRESHOLDS",guard.assess(root,0,2,100)["issues"])

if __name__=="__main__":unittest.main()
