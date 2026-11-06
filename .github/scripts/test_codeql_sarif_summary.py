#!/usr/bin/env python3
"""Negative and privacy tests for CodeQL SARIF redacted accounting."""
import json
from pathlib import Path
import tempfile
import unittest
import codeql_sarif_summary as summary

def sarif(path="experiments/trapnet-zero-trust/cmd/sensor/main.go"):
    return {"version":"2.1.0","runs":[{"results":[
        {"ruleId":"go/missing-error-check","level":"warning",
         "message":{"text":"secret attacker password must never appear"},
         "locations":[{"physicalLocation":{"artifactLocation":{"uri":path},"region":{"startLine":42}}}]},
        {"ruleId":"go/missing-error-check","level":"error","locations":[]}
    ]}]}

class SummaryTests(unittest.TestCase):
    def test_counts_and_no_raw_messages(self):
        rules,levels,examples=summary.extract(sarif())
        self.assertEqual(rules["go/missing-error-check"],2)
        self.assertEqual(levels["error"],1)
        self.assertEqual(levels["warning"],1)
        self.assertEqual(examples[0]["line"],42)
        self.assertNotIn("password",json.dumps(examples))

    def test_path_redaction(self):
        for path in ("/home/user/.ssh/id", "../private", "https://example.com/x",
                     "x\\y", "name\nunsafe"):
            with self.subTest(path=path):
                self.assertEqual(summary.extract(sarif(path))[2][0]["file"],"<redacted>")

    def test_invalid_sarif_fails(self):
        for data in (None, {}, {"version":"1.0"}, {"version":"2.1.0","runs":[]}):
            with self.assertRaises(ValueError):
                summary.extract(data)

    def test_missing_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                summary.summarize(temp,"go",str(Path(temp)/"result.json"))

    def test_realistic_output(self):
        with tempfile.TemporaryDirectory() as temp:
            inp=Path(temp)/"go.sarif"
            inp.write_text(json.dumps(sarif()),encoding="utf8")
            out=Path(temp)/"summary.json"
            result=summary.summarize(temp,"go",str(out))
            self.assertEqual(result["sarif_results_not_unique_alerts"],2)
            self.assertFalse(result["human_reviewed"])
            self.assertEqual(result["formal_release"],"HOLD")
            self.assertNotIn("password",out.read_text(encoding="utf8"))

    def test_unsafe_language_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                summary.summarize(temp,"secrets",str(Path(temp)/"summary.json"))

if __name__=="__main__":
    unittest.main()
