import json
from pathlib import Path
import tempfile
import unittest

import release_gate
import sonar_parity

class BetaGateTests(unittest.TestCase):
    def test_empty_evidence_refuses_go(self):
        r=release_gate.assess({})
        self.assertFalse(r["ready_for_human_decision"])
        self.assertFalse(r["publication_executed"])
        self.assertEqual(len(r["missing"]),len(release_gate.REQUIREMENTS))
    def test_bare_booleans_do_not_pass(self):
        r=release_gate.assess({"checks":{k:True for k in release_gate.REQUIREMENTS}})
        self.assertFalse(r["ready_for_human_decision"])
    def test_full_evidence_still_does_not_publish(self):
        checks={k:{"passed":True,"evidence":"https://example.invalid/reviewer-signoff"} for k in release_gate.REQUIREMENTS}
        r=release_gate.assess({"checks":checks})
        self.assertTrue(r["ready_for_human_decision"])
        self.assertFalse(r["publication_executed"])

class SourceParityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for path in sonar_parity.FILES:
            target=self.root/path
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(b"independent source sample")
    def test_matches_independent_manifest(self):
        manifest=sonar_parity.inventory(self.root)
        self.assertTrue(sonar_parity.compare(manifest,manifest)["matches_pinned_inventory"])
        self.assertFalse(manifest["self_attestation"])
    def test_tamper_detected(self):
        manifest=sonar_parity.inventory(self.root)
        (self.root/"web/decoy.py").write_bytes(b"changed")
        result=sonar_parity.compare(manifest,sonar_parity.inventory(self.root))
        self.assertEqual(result["difference_paths"],["web/decoy.py"])
    def test_symlinked_code_refused(self):
        target=self.root/"web/decoy.py"
        target.unlink()
        try:target.symlink_to(self.root/"web/decoy_expansion.py")
        except OSError:self.skipTest("no symlink privileges")
        with self.assertRaises(ValueError):sonar_parity.inventory(self.root)
    def test_partial_inventory_refused(self):
        manifest=sonar_parity.inventory(self.root)
        manifest["files"].pop("web/decoy.py")
        with self.assertRaises(ValueError):sonar_parity.compare(manifest,sonar_parity.inventory(self.root))
if __name__=="__main__":unittest.main()
