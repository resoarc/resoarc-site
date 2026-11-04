import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime,timezone

import retention_offline as tool

@unittest.skipUnless(os.name=="posix" and hasattr(os,"O_DIRECTORY"),
                     "needs Linux dirfd/no-follow security semantics")
class RetentionOnlyOfflineTests(unittest.TestCase):
    def setUp(self):
        self.parent=Path(tempfile.mkdtemp(prefix="trapnet-e1-test-parent-"))
        self.root=self.parent/(tool.STAGE+"testing")
        self.root.mkdir(mode=0o700)
        self.marker=self.root/tool.SENTINEL
        self.marker.write_text(json.dumps({"schema":tool.VERSION,"synthetic_only":True}),encoding="utf-8")
        self.marker.chmod(0o600)
        self.old=self.root/"cowrie-20200101T000000Z-0123456789abcdef.jsonl"
        self.recent=self.root/"cowrie-20260101T000000Z-fedcba9876543210.jsonl"
        self.old.write_bytes(b"synthetic IP 198.51.100.10 no export\n")
        self.recent.write_bytes(b"synthetic recent IP 192.0.2.25 no export\n")
        for path in (self.old,self.recent):
            path.chmod(0o600)
        self.cutoff=tool.parse_cutoff("2024-01-01T00:00:00Z")
        os.utime(self.old,ns=(self.cutoff-86400*10**9,self.cutoff-86400*10**9))
        os.utime(self.recent,ns=(self.cutoff+86400*10**9,self.cutoff+86400*10**9))

    def tearDown(self):
        shutil.rmtree(self.parent,ignore_errors=True)

    def test_default_dry_run_deletes_nothing(self):
        result=tool.action(self.root,self.cutoff)
        self.assertEqual(result["status"],"DRY_RUN")
        self.assertEqual(result["candidate_old"],1)
        self.assertEqual(result["preserved_recent"],1)
        self.assertEqual(result["deleted"],0)
        self.assertTrue(self.old.exists())
        self.assertTrue(self.recent.exists())

    def test_explicit_plan_can_delete_only_old_synthetic_log(self):
        plan=tool.action(self.root,self.cutoff)["plan_sha256"]
        preserved=self.recent.read_bytes()
        result=tool.action(self.root,self.cutoff,plan)
        self.assertEqual(result["status"],"APPLIED_TO_SYNTHETIC_STAGE")
        self.assertEqual(result["deleted"],1)
        self.assertFalse(self.old.exists())
        self.assertEqual(self.recent.read_bytes(),preserved)

    def test_wrong_approval_sha_refuses_deletion(self):
        with self.assertRaisesRegex(ValueError,"approved manifest"):
            tool.action(self.root,self.cutoff,"0"*64)
        self.assertTrue(self.old.exists())

    def test_changed_file_after_approval_refuses(self):
        plan=tool.action(self.root,self.cutoff)["plan_sha256"]
        with self.old.open("ab") as f:
            f.write(b"change")
        with self.assertRaisesRegex(ValueError,"approved manifest"):
            tool.action(self.root,self.cutoff,plan)
        self.assertTrue(self.old.exists())

    def test_symlink_log_refuses(self):
        self.old.unlink()
        self.old.symlink_to(self.recent)
        with self.assertRaises(ValueError):
            tool.action(self.root,self.cutoff)

    def test_symlink_root_refuses(self):
        alias=self.parent/(tool.STAGE+"alias")
        alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):
            tool.action(alias,self.cutoff)

    def test_hardlinks_refused(self):
        linked=self.parent/"outside-hardlink.txt"
        os.link(self.old,linked)
        with self.assertRaises(ValueError):
            tool.action(self.root,self.cutoff)

    def test_world_readable_raw_logs_refused(self):
        self.old.chmod(0o644)
        with self.assertRaises(ValueError):
            tool.action(self.root,self.cutoff)

    def test_unexpected_entry_refuses_entire_plan(self):
        (self.root/"cowrie.json").write_text("unexpected",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"unexpected entry"):
            tool.action(self.root,self.cutoff)

    def test_missing_or_corrupted_offline_sentinel_refuses(self):
        self.marker.unlink()
        with self.assertRaises(OSError):
            tool.action(self.root,self.cutoff)
        self.marker.write_text('{"synthetic_only":false}',encoding="utf-8")
        self.marker.chmod(0o600)
        with self.assertRaises(ValueError):
            tool.action(self.root,self.cutoff)

    def test_invalid_or_future_cutoff_refused(self):
        for invalid in ("tomorrow","2026-02-30T12:00:00Z","2026-01-01 12:00:00Z"):
            with self.assertRaises(ValueError):
                tool.parse_cutoff(invalid)

    def test_unowned_or_open_staging_directory_refused(self):
        self.root.chmod(0o777)
        with self.assertRaises(ValueError):
            tool.action(self.root,self.cutoff)

    def test_non_staging_directory_never_accepted(self):
        wrong=self.parent/"real-cowrie-log"
        wrong.mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            tool.action(wrong,self.cutoff)

    def test_sanitized_result_never_outputs_raw_content(self):
        output=tool.action(self.root,self.cutoff)
        body=json.dumps(output)
        self.assertNotIn("198.51.100",body)
        self.assertNotIn("192.0.2",body)
        self.assertNotIn(self.old.name,body)
        self.assertNotIn(str(self.root),body)
        self.assertFalse(output["production_modified"])

if __name__=="__main__":
    unittest.main()
