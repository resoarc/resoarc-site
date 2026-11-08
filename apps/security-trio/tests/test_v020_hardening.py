"""Security regression corpus: known failure modes fixed in v0.2.0."""
from __future__ import annotations

import csv
import io
import json
import re
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

import app
import common
import file_inspector
import log_lantern
import secret_scout


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="resoarc-hardening-")
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else value.encode("utf-8"))
        return path

    def line(self, address: str, resource: str = "/.env", status: int = 404):
        return (f'{address} - - [08/Nov/2026:01:03:03 +0900] '
                f'"GET {resource} HTTP/1.1" {status} 123 "-" "Test"\n')

    def test_url_path_long_token_redacted(self):
        token = "ResetToken_" + "Aa1b2C3d4E5f6G7h8I9j0"
        self.assertNotIn(token, common.redact_url("/password/reset/" + token))
        self.assertEqual(common.redact_url("/password/reset/" + token), "/password/reset/[REDACTED]")

    def test_url_percent_encoded_email_redacted(self):
        self.assertEqual(common.redact_url("/users/alice%40example.org/orders?x=s3cr3t"),
                         "/users/[REDACTED]/orders")

    def test_url_absolute_removes_userinfo_and_query(self):
        output = common.redact_url("https://admin:" + "password@example.org/v1/data?token=abc")
        self.assertEqual(output, "/v1/data")

    def test_url_percent_encoded_question_marks(self):
        self.assertEqual(common.redact_url("/orders%3Ftoken%3Dpassword"), "/orders")

    def test_log_path_secrets_not_in_json_export(self):
        secret = "Aa1b2C3d4E5f6G7h8I9j0K1l2"
        p = self.write("access.log", self.line("198.51.100.44", f"/reset/{secret}?token=nonpublic"))
        result = log_lantern.scan([p])
        data = json.dumps(result.export_data())
        self.assertNotIn(secret, data)
        self.assertNotIn("nonpublic", data)

    def test_iis_query_injection_detected_but_not_exported(self):
        secret = "private_password_NEVER_EXPORT"
        lines = ("#Fields: date time c-ip cs-method cs-uri-stem cs-uri-query sc-status\n"
                 f"2026-11-08 01:01:01 198.51.100.44 GET /view filter=union%20select%20{secret} 200\n")
        out = log_lantern.scan([self.write("iis.log", lines)])
        self.assertTrue(any("SQL" in f.rule for f in out.findings))
        self.assertNotIn(secret, json.dumps(out.export_data()))
        self.assertEqual(out.metrics["popular_paths"][0]["path"], "/view")

    def test_distinct_hosts_share_prefix_stay_separate(self):
        p = self.write("access.log", self.line("198.51.100.44") + self.line("198.51.101.45"))
        result = log_lantern.scan([p])
        findings = [f for f in result.findings if "秘密" in f.rule]
        self.assertEqual(len(findings), 2)
        self.assertNotEqual(findings[0].target, findings[1].target)
        serialized = json.dumps(result.export_data())
        self.assertNotIn("198.51.100.44", serialized)
        self.assertNotIn("198.51.101.45", serialized)

    def test_same_host_repeated_requests_combined(self):
        p = self.write("access.log", self.line("198.51.100.44") * 3)
        result = log_lantern.scan([p])
        findings = [f for f in result.findings if "秘密" in f.rule]
        self.assertEqual(len(findings), 1)
        self.assertIn("3 件", findings[0].detail)

    def test_no_findings_but_skipped_cli_is_incomplete(self):
        p = self.write("binary.png", b"not an actual PNG")
        with __import__('contextlib').redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_cli("secret", [str(p)], None, "json"), 2)

    def test_partial_read_failure_cli_is_incomplete(self):
        valid = self.write("valid.log", self.line("198.51.100.44", "/health", 200))
        missing = self.folder / "missing.log"
        # Deliberately mix an invalid format with valid access entries.
        garbage = self.write("garbage.log", "unrecognized record\n")
        with __import__('contextlib').redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_cli("log", [str(valid), str(missing), str(garbage)], None, "json"), 2)

    def test_report_never_overwrites_direct_input(self):
        p = self.write("report.json", "password=abcDEFghi123456")
        self.assertTrue(common.output_overwrites_input(p, [str(p)]))
        with __import__('contextlib').redirect_stderr(io.StringIO()):
            self.assertEqual(app.run_cli("secret", [str(p)], str(p), "json"), 2)
        self.assertEqual(p.read_text(), "password=abcDEFghi123456")

    def test_csv_reports_unparsed_lines(self):
        r = common.ScanResult("test", metrics={"unparsed_lines": 8})
        f = self.folder / "report.csv"
        common.export_csv(f, r)
        self.assertIn("8 行", f.read_text(encoding="utf-8-sig"))

    def test_csv_contains_skipped_warning(self):
        r = common.ScanResult("test", scanned=1, skipped=2)
        f = self.folder / "report.csv"
        common.export_csv(f, r)
        text = f.read_text(encoding="utf-8-sig")
        self.assertIn("未検査の項目あり", text)
        self.assertIn("2 件", text)

    def test_csv_contains_errors_and_truncation(self):
        r = common.ScanResult("test", truncated=True, errors=["制限を超えています"])
        f = self.folder / "report.csv"
        common.export_csv(f, r)
        text = f.read_text(encoding="utf-8-sig")
        self.assertIn("検査は未完了", text)
        self.assertIn("解析上の制限", text)
        self.assertIn("制限を超えています", text)

    def test_csv_error_formula_neutralized(self):
        r = common.ScanResult("test", errors=['=HYPERLINK("https://example.invalid")'])
        f = self.folder / "report.csv"
        common.export_csv(f, r)
        with f.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        self.assertTrue(any(row[3].startswith("'=HYPERLINK") for row in rows[1:]))

    def test_filename_email_mask(self):
        self.assertNotIn("alice@example.org", common.safe_name("alice@example.org-report.txt"))

    def test_filename_long_id_mask(self):
        self.assertNotIn("a"*34, common.safe_name("data-" + "a"*34 + ".json"))

    def test_live_credential_containing_sample_still_detected(self):
        p = self.write("secret.env", "password=q8X4sample9l27A1bX\n")
        self.assertTrue(secret_scout.scan([p]).findings)

    def test_known_format_with_example_fragment_still_detected(self):
        token = "ghp_" + "aBcExampleDef" + "5Hj7K9l1m2N4p6Q8r0S2t4U6v8"
        p = self.write("config.txt", "AUTH_TOKEN=" + token)
        out = secret_scout.scan([p])
        self.assertTrue(any(f.rule == "GitHubトークン形式" for f in out.findings))
        self.assertNotIn(token, json.dumps(out.export_data()))

    def test_pdf_masquerading_as_png(self):
        p = self.write("picture.png", b"%PDF-1.7\n%%EOF")
        out = file_inspector.scan([p])
        self.assertTrue(any(f.rule == "拡張子と実形式が不一致" for f in out.findings))

    def test_png_masquerading_as_pdf(self):
        p = self.write("invoice.pdf", b"\x89PNG\r\n\x1a\n" + b"\0"*80)
        out = file_inspector.scan([p])
        self.assertTrue(any(f.rule == "拡張子と実形式が不一致" for f in out.findings))

    def test_benign_pdf_no_mismatch(self):
        p = self.write("invoice.pdf", b"%PDF-1.7\n%%EOF")
        out = file_inspector.scan([p])
        self.assertFalse(any(f.rule == "拡張子と実形式が不一致" for f in out.findings))

    def test_unsupported_file_magic_remains_unknown(self):
        p = self.write("image.png", b"random data")
        out = file_inspector.scan([p])
        self.assertFalse(any(f.rule == "拡張子と実形式が不一致" for f in out.findings))

    def test_zip_does_not_extract_to_disk(self):
        p = self.folder / "documents.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("../escape.txt", "test")
        file_inspector.scan([p])
        self.assertFalse((self.folder.parent / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
