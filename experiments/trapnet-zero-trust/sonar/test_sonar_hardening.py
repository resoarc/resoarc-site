import io
import json
import unittest
import sonar_hardening as s

class PrivacyChecks(unittest.TestCase):
    def test_no_raw_values(self):
        data='{"path":"/api/items","status":200,"source":"private","user_agent":"unknown"}\n'*8
        obj=s.aggregate(io.StringIO(data))
        result=json.dumps(obj)
        self.assertNotIn("source",result.replace('"log_source_status"',''))
        self.assertNotIn("/api/items",result)
        self.assertEqual(obj["path_category_bands"]["api"],"5-9")
    def test_suppression(self):
        obj=s.aggregate(io.StringIO('{"path":"/admin","status":403}\n'))
        self.assertEqual(obj["path_category_bands"],{})
    def test_not_proven(self):
        obj=s.evasion([{"cohort":"known","events":1,"exposure_hours":12}])
        self.assertFalse(obj["causal_attribution"])
    def test_local_scope(self):
        with self.assertRaises(ValueError):
            s.fingerprint_local(host="8.8.8.8")

if __name__=="__main__":
    unittest.main()
