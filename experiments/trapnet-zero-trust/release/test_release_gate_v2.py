import unittest
import release_gate

SHA="a"*40
DIGEST="b"*64
REF="https://github.com/resoarc/resoarc-site/actions/runs/123456789"
def full():
 return {"source_commit_sha":SHA,"candidate_sha256":DIGEST,"checks":{
    key:{"passed":True,"evidence":REF,"source_commit_sha":SHA,"candidate_sha256":DIGEST}
    for key in release_gate.REQUIREMENTS
 }}
class GateV2Tests(unittest.TestCase):
 def test_empty(self):
  r=release_gate.assess({})
  self.assertFalse(r["ready_for_human_decision"])
  self.assertFalse(r["publication_executed"])
  self.assertEqual(r["complete"],0)
 def test_full_still_does_not_publish(self):
  r=release_gate.assess(full())
  self.assertTrue(r["ready_for_human_decision"])
  self.assertFalse(r["publication_executed"])
 def test_old_commit_refused(self):
  e=full()
  e["checks"]["ci_go_and_security_green"]["source_commit_sha"]="c"*40
  self.assertFalse(release_gate.assess(e)["ready_for_human_decision"])
 def test_other_binary_refused(self):
  e=full()
  e["checks"]["independent_security_review"]["candidate_sha256"]="c"*64
  self.assertFalse(release_gate.assess(e)["ready_for_human_decision"])
 def test_boolean_and_local_file_refused(self):
  e=full()
  e["checks"]["release_manager_approval"]=True
  e["checks"]["source_revision_pinned"]["evidence"]="file:///tmp/approval"
  self.assertFalse(release_gate.assess(e)["ready_for_human_decision"])
 def test_unpinned_revision_refused(self):
  e=full()
  e["source_commit_sha"]="not-a-commit"
  self.assertEqual(release_gate.assess(e)["complete"],0)
 def test_url_validation(self):
  for url in ("javascript:run()","http://example.com/evil","https://user@github.com/x","https://example.invalid","https://a/b\n"):
   self.assertFalse(release_gate.evidence_reference(url))
  self.assertTrue(release_gate.evidence_reference(REF))
if __name__=="__main__":unittest.main()
