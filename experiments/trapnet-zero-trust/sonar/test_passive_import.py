import json
import os
import pathlib
import tempfile
import unittest

import passive_import

class PassiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/"authorized.log"
        self.path.write_text(
           '198.51.100.20 - - [01/Oct/2026] "GET /admin/login?secret=do-not-export HTTP/1.1" 404 10 "-" "UserAgent"\n'*7,
           encoding="utf-8"
        )
    def test_requires_authorization(self):
        with self.assertRaises(ValueError):
            passive_import.process(self.path,"authorized_web_server",False)
    def test_rejects_unknown_source(self):
        with self.assertRaises(ValueError):
            passive_import.process(self.path,"other_logs",True)
    def test_never_exports_raw_details(self):
        result=passive_import.process(self.path,"authorized_web_server",True)
        raw=json.dumps(result)
        for private in ("198.51.100.20","do-not-export","UserAgent","/admin/login"):
            self.assertNotIn(private,raw)
        self.assertEqual(result["path_category_bands"]["auth"],"5-9")
        self.assertFalse(result["sent_to_hub"])
    def test_private_file_mode_and_no_overwrite(self):
        out=pathlib.Path(self.temp.name)/"report.json"
        passive_import.save_private_new(out,passive_import.process(self.path,"authorized_web_server",True))
        self.assertTrue(out.is_file())
        if os.name=="posix":
            self.assertEqual(out.stat().st_mode & 0o777,0o600)
        with self.assertRaises(ValueError):
            passive_import.save_private_new(out,{})
    def test_rejects_input_symlink(self):
        link=pathlib.Path(self.temp.name)/"link.log"
        try:link.symlink_to(self.path)
        except (OSError,NotImplementedError):self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            passive_import.process(link,"authorized_web_server",True)
    def test_suppresses_singletons(self):
        self.path.write_text('{"path":"/admin","status":403}\n',encoding="utf-8")
        r=passive_import.process(self.path,"authorized_web_server",True)
        self.assertEqual(r["path_category_bands"],{})
if __name__=="__main__":unittest.main()
