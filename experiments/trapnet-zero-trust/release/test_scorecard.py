import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import scorecard

class ReleaseGateScorecardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(scorecard.MANIFEST.read_text(encoding="utf-8"))

    def clone(self):
        return copy.deepcopy(self.base)

    def item(self,data,id):
        return next(g for g in data["gates"] if g["id"]==id)

    def test_twenty_gate_accounts_and_release_hold(self):
        data=self.clone()
        self.assertTrue(scorecard.validate(data))
        self.assertEqual(scorecard.counts(data["gates"],"technical_status"),
                         {"PASS":2,"PARTIAL":16,"TODO":2})
        self.assertEqual(scorecard.counts(data["gates"],"release_status"),
                         {"PASS":1,"PARTIAL":17,"TODO":2})
        self.assertEqual(data["release_authorization"],"HOLD")

    def test_a2_technical_pass_does_not_fake_formal_release_pass(self):
        a2=self.item(self.clone(),"A2")
        self.assertEqual(a2["technical_status"],"PASS")
        self.assertEqual(a2["release_status"],"PARTIAL")
        self.assertIn("D3",a2["dependencies"])
        self.assertIn("E3",a2["dependencies"])
        self.assertIn("45/45",a2["evidence_summary"])

    def test_cannot_mark_gate_formal_without_human_review_record(self):
        data=self.clone()
        self.item(data,"A2")["release_status"]="PASS"
        with self.assertRaisesRegex(ValueError,"independent review"):
            scorecard.validate(data)

    def test_scoped_formal_review_can_close_before_global_release(self):
        # A hypothetical structurally complete external review can close A2
        # independently of D3/E3. This test does not authenticate a reviewer,
        # and NEVER edits the actual manifest.
        data=self.clone()
        a2=self.item(data,"A2")
        a2["release_status"]="PASS"
        a2["review_approval"]={
            "reviewer":"unverified-test-reviewer",
            "verified_commit":"495a550a8faa3ce198daa1043bfd4d2ad98346a5",
            "evidence_uri":"https://example.invalid/ci",
            "signed_decision_uri":"https://example.invalid/decision"
        }
        self.assertTrue(scorecard.validate(data))
        self.assertEqual(data["release_authorization"],"HOLD")
        self.assertEqual(self.item(data,"D3")["release_status"],"PARTIAL")
        self.assertEqual(self.item(data,"E3")["release_status"],"TODO")
        data["release_authorization"]="READY"
        with self.assertRaisesRegex(ValueError,"release READY"):
            scorecard.validate(data)

    def test_cannot_infer_technical_pass_from_partial_test(self):
        data=self.clone()
        self.item(data,"B2")["technical_status"]="PASS"
        with self.assertRaisesRegex(ValueError,"own work incomplete"):
            scorecard.validate(data)

    def test_technical_pass_must_have_pinned_evidence(self):
        data=self.clone()
        self.item(data,"A2")["technical_evidence"]=[]
        with self.assertRaisesRegex(ValueError,"pinned evidence"):
            scorecard.validate(data)
        data=self.clone()
        self.item(data,"A2")["technical_evidence"][0]["sha256"]="bad"
        with self.assertRaisesRegex(ValueError,"unpinned technical proof"):
            scorecard.validate(data)

    def test_technical_ci_proof_requires_correct_repository_and_commit(self):
        data=self.clone()
        self.item(data,"A2")["technical_evidence"][1]["uri"]="https://example.invalid/runs/123"
        with self.assertRaisesRegex(ValueError,"wrong CI origin"):
            scorecard.validate(data)

    def test_local_pinned_legacy_proof_matches_and_detects_tampering(self):
        # Portable deterministic unit test; it never needs a private
        # machine's absolute file path in public CI.
        data=self.clone()
        a1=self.item(data,"A1")
        with tempfile.TemporaryDirectory() as root:
            sample=b'{"test":"synthetic-private-fixture","passed":true}\\n'
            path=Path(root)/"v027-cowrie-enospc.json"
            path.write_bytes(sample)
            a1["technical_evidence"][0]["sha256"]=hashlib.sha256(sample).hexdigest()
            self.assertEqual(scorecard.verify_local_files(data,root),[])
            path.write_bytes(sample+b"tampered")
            self.assertTrue(scorecard.verify_local_files(data,root))
        self.assertTrue(scorecard.verify_local_files(data,None))

    def test_cannot_release_ready_from_green_ci(self):
        data=self.clone()
        data["release_authorization"]="READY"
        with self.assertRaisesRegex(ValueError,"release READY"):
            scorecard.validate(data)

    def test_cannot_demote_formal_below_technical(self):
        data=self.clone()
        self.item(data,"A2")["technical_status"]="TODO"
        self.item(data,"A2")["release_status"]="PASS"
        with self.assertRaisesRegex(ValueError,"formal PASS without technical PASS"):
            scorecard.validate(data)

    def test_must_have_exactly_20_unique_gate_ids(self):
        data=self.clone()
        data["gates"][-1]["id"]="A1"
        with self.assertRaisesRegex(ValueError,"ID duplication"):
            scorecard.validate(data)

    def test_reports_all_twenty_and_explicit_hold(self):
        result=scorecard.report(self.clone())
        self.assertIn("| ゲート固有の技術受入 | 2 | 16 | 2 |",result)
        self.assertIn("| 従来の正式リリースゲート | 1 | 17 | 2 |",result)
        self.assertIn("A2",result)
        self.assertIn("D3",result)
        self.assertIn("E3",result)
        self.assertIn("HOLD",result)

if __name__=="__main__":
    unittest.main()
