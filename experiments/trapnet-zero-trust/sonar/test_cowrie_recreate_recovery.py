import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import cowrie_recreate_recovery as lab

class RecreateRecoveryUnitTests(unittest.TestCase):
    def sample(self, directory, count=1):
        p=Path(directory)/"log/cowrie";p.mkdir(parents=True,exist_ok=True)
        with (p/"cowrie.json").open("w",encoding="utf8") as f:
            for i in range(count):
                f.write(json.dumps({"eventid":"cowrie.session.connect","session":str(i)})+"\n")
        return p/"cowrie.json"
    def test_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            self.sample(d,2)
            data,count,connections=lab.snapshot(Path(d))
            self.assertEqual((count,connections),(2,2))
            self.assertTrue(data)
    def test_log_deleted_after_container_removal_fails(self):
        with tempfile.TemporaryDirectory() as d:
            f=self.sample(d)
            old=lab.snapshot(Path(d))[0]
            f.unlink()
            with self.assertRaises(ValueError):
                lab.verify_log_continuity(old,Path(d))
    def test_log_rewrite_is_not_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            f=self.sample(d,2)
            old=lab.snapshot(Path(d))[0]
            f.write_text(json.dumps({"eventid":"cowrie.session.connect","session":"new"})+"\n")
            with self.assertRaises(ValueError):
                lab.verify_log_continuity(old,Path(d))
    def test_append_is_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            f=self.sample(d)
            old=lab.snapshot(Path(d))[0]
            with f.open("a") as stream:
                stream.write(json.dumps({"eventid":"cowrie.session.connect","session":"after"})+"\n")
            new,total,connections=lab.verify_log_continuity(old,Path(d))
            self.assertEqual((total,connections),(2,2))
            self.assertTrue(new.startswith(old))
    def test_malformed_log_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=self.sample(d)
            old=lab.snapshot(Path(d))[0]
            with f.open("a") as stream:stream.write("not-json\n")
            with self.assertRaises(json.JSONDecodeError):
                lab.verify_log_continuity(old,Path(d))
    def test_symlinked_image_defaults_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"sub").mkdir()
            (root/"sub"/"link").symlink_to(root,target_is_directory=True)
            with self.assertRaises(ValueError):
                lab.default_config_is_regular(root)
    def test_regular_image_defaults_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"sub").mkdir()
            (root/"sub"/"settings").write_text("mock")
            lab.default_config_is_regular(root)

if __name__=="__main__":unittest.main()
