import json
import unittest
import cowrie_gap_advice as a

def health(issues=None,passed=False):
    return {"schema":"trapnet.cowrie-log-health.v1",
            "passed":passed,"issues":issues or []}

class GapAdviceTests(unittest.TestCase):
    def test_storage_exhaustion_maps_to_gap(self):
        r=a.decide(health(["FREE_SPACE_LOW"]))
        self.assertEqual(r["gap_reason"],"storage_full")
        self.assertTrue(r["gap_notice_recommended"])
    def test_torn_json_maps_to_corruption(self):
        self.assertEqual(a.decide(health(["JSON_LINE_INVALID"]))["gap_reason"],"log_corrupt")
    def test_missing_log_maps_to_unavailable(self):
        self.assertEqual(a.decide(health(["JSON_LOG_MISSING"]))["gap_reason"],"log_unavailable")
    def test_multiple_reasons_prioritize_storage(self):
        self.assertEqual(a.decide(health(["JSON_LINE_INVALID","FREE_SPACE_LOW"]))["gap_reason"],"storage_full")
    def test_unbounded_capacity_does_not_fabricate_gap(self):
        r=a.decide(health(["VOLUME_LIMIT_NOT_PROVEN"]))
        self.assertEqual(r["status"],"INSPECTION_HOLD")
        self.assertFalse(r["gap_notice_recommended"])
    def test_bounded_log_is_not_all_clear(self):
        r=a.decide(health(passed=True))
        self.assertEqual(r["status"],"SNAPSHOT_PARSEABLE_COVERAGE_UNPROVEN")
        self.assertFalse(r["observation_coverage_proven"])
        self.assertFalse(r["automatic_clear"])
    def test_invalid_health_data_holds(self):
        self.assertEqual(a.decide({"schema":"unknown"})["status"],"INSPECTION_HOLD")
    def test_nonlist_issues_holds(self):
        self.assertEqual(a.decide({"schema":"trapnet.cowrie-log-health.v1","issues":"FREE_SPACE_LOW"})["status"],"INSPECTION_HOLD")
    def test_no_automatic_transport_or_clear(self):
        for x in (health(["FREE_SPACE_LOW"]),health(["VOLUME_LIMIT_NOT_PROVEN"]),health(passed=True),None):
            r=a.decide(x)
            self.assertFalse(r["automatic_send"])
            self.assertFalse(r["automatic_clear"])
    def test_sensitive_raw_data_never_echoed(self):
        r=a.decide({"schema":"trapnet.cowrie-log-health.v1",
             "issues":["FREE_SPACE_LOW"],"src_ip":"192.0.2.9",
             "token":"private-secret"})
        serialized=json.dumps(r)
        self.assertNotIn("192.0.2.9",serialized)
        self.assertNotIn("private-secret",serialized)
    def test_unknown_or_attacker_controlled_issue_not_printed(self):
        r=a.decide(health(["attacker\\nSHELL_COMMAND"]))
        self.assertEqual(r["status"],"INSPECTION_HOLD")
        self.assertNotIn("SHELL_COMMAND",json.dumps(r))

if __name__=="__main__":unittest.main()
