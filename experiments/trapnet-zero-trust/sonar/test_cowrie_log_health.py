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
        with patch.object(guard.os,"fstatvfs",return_value=stat(free,capacity)):
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
    def test_identical_log_line_duplicate_refused_without_data_export(self):
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d)
            line=path.read_bytes()
            path.write_bytes(line+line)
            result=self.assess_with(root)
            self.assertFalse(result['passed'])
            self.assertIn('JSON_LINE_DUPLICATE',result['issues'])
            self.assertNotIn('PRIVATE',json.dumps(result))

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

    def test_actual_log_mount_must_be_bounded(self):
        # The var root may be a small tmpfs while log/ is a host bind mount.
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            with patch.object(guard.os,"fstatvfs",side_effect=[
                stat(capacity=8*1024*1024),stat(capacity=128*1024*1024)
            ]):
                result=guard.assess(root)
            self.assertIn("VOLUME_LIMIT_NOT_PROVEN",result["issues"])
            self.assertFalse(result["passed"])

    def test_both_root_and_log_filesystems_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            with patch.object(guard.os,"fstatvfs",side_effect=[
                stat(capacity=128*1024*1024),stat(capacity=8*1024*1024)
            ]):
                result=guard.assess(root)
            self.assertIn("VOLUME_LIMIT_NOT_PROVEN",result["issues"])

    def test_actual_log_mount_low_free_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            with patch.object(guard.os,"fstatvfs",side_effect=[
                stat(free=4*1024*1024),stat(free=0)
            ]):
                result=guard.assess(root)
            self.assertIn("FREE_SPACE_LOW",result["issues"])

    def test_symlink_swap_between_check_and_open_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d)
            original=root/"private.json"
            real_open=guard.os.open
            swapped=[False]
            def intervening_open(name,flags,*args,**kwargs):
                if name=="cowrie.json" and not swapped[0]:
                    swapped[0]=True
                    path.rename(original)
                    path.symlink_to(original)
                return real_open(name,flags,*args,**kwargs)
            try:
                with patch.object(guard.os,"open",side_effect=intervening_open):
                    result=self.assess_with(root)
            except OSError as exc:
                self.skipTest("symlink unavailable: "+type(exc).__name__)
            self.assertTrue(swapped[0])
            self.assertFalse(result["passed"])
            self.assertIn("IO_OR_FORMAT_ERROR",result["issues"])

    def test_concurrent_file_rewrite_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d)
            real_loads=guard.json.loads
            mutated=[False]
            def mutate_during_read(raw,*args,**kwargs):
                if not mutated[0] and isinstance(raw,bytes):
                    mutated[0]=True
                    path.write_text(json.dumps({"eventid":"cowrie.session.close"})+"\\n")
                return real_loads(raw,*args,**kwargs)
            with patch.object(guard.json,"loads",side_effect=mutate_during_read):
                result=self.assess_with(root)
            self.assertTrue(mutated[0])
            self.assertFalse(result["passed"])
            self.assertIn("LOG_CHANGED_WHILE_READING",result["issues"])

    def test_hardlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d)
            other=root/"copied-hardlink.json"
            try:guard.os.link(path,other)
            except OSError:self.skipTest("hardlinks unavailable")
            result=self.assess_with(root)
            self.assertFalse(result["passed"])
            self.assertIn("JSON_LOG_TYPE_UNSAFE",result["issues"])

    def test_non_regular_fifo_does_not_block(self):
        if not hasattr(guard.os,"mkfifo"):self.skipTest("FIFO unsupported")
        with tempfile.TemporaryDirectory() as d:
            root,path=self.fixture(d)
            path.unlink()
            guard.os.mkfifo(path)
            result=self.assess_with(root)
            self.assertFalse(result["passed"])
            self.assertIn("JSON_LOG_TYPE_UNSAFE",result["issues"])

    def test_report_never_claims_release_approval(self):
        with tempfile.TemporaryDirectory() as d:
            root,_=self.fixture(d)
            report=self.assess_with(root)
            self.assertFalse(report["public_beta_ready"])
            self.assertFalse(report["new_event_append_proven"])
            self.assertFalse(report["sensitive_log_content_exported"])

if __name__=="__main__":unittest.main()
