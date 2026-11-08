"""Regression corpus for rc3 privacy, Office spoofing and memory ceilings."""
from __future__ import annotations
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import file_inspector
import log_lantern
import secret_scout
from common import export_json, redact_url, safe_name


class PrivacyAndAccuracy(unittest.TestCase):
    def test_reset_token_short_hidden(self):
        self.assertEqual(redact_url('/reset/aBcd12Ef'), '/reset/[REDACTED]')

    def test_invite_token_letters_hidden(self):
        self.assertEqual(redact_url('/invite/abcdefghijkl'), '/invite/[REDACTED]')

    def test_double_encoded_route_hidden(self):
        self.assertEqual(redact_url('/%2572eset/shorttoken'), '/reset/[REDACTED]')

    def test_inline_secret_hidden(self):
        self.assertEqual(redact_url('/api/access_token=short1'), '/api/[REDACTED]')

    def test_short_credential_in_filename_hidden(self):
        self.assertEqual(safe_name("token=x"), "[CREDENTIAL]")
        self.assertEqual(safe_name("password=abc.txt"), "[CREDENTIAL]")

    def test_registration_token_redacted(self):
        self.assertEqual(redact_url("/register/code123"), "/register/[REDACTED]")

    def test_normal_route_still_readable(self):
        self.assertEqual(redact_url('/article/hello-world/overview'), '/article/hello-world/overview')

    def test_url_with_query_fragment_not_exported(self):
        self.assertEqual(redact_url('/reset/token123?email=someone@example.com#secret'), '/reset/[REDACTED]')

    def test_json_export_never_contains_reset_token(self):
        with tempfile.TemporaryDirectory() as td:
            input_path = Path(td) / 'access.log'
            secret = 'PRIVATE_DEMO_TOKEN'
            input_path.write_text(
                '203.0.113.18 - - [08/Nov/2026:01:03:02 +0900] '
                '"GET /reset/' + secret + '?k=HIDDEN HTTP/1.1" 200 120 "-" "UnitTest"\n',
                encoding='utf-8')
            report = log_lantern.scan([input_path])
            output = Path(td) / 'report.json'
            export_json(output, report)
            self.assertNotIn(secret, output.read_text(encoding='utf-8'))
            self.assertNotIn('HIDDEN', output.read_text(encoding='utf-8'))

    def test_renamed_zip_as_docx_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'invoice.docx'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('random.txt', 'hello')
            report = file_inspector.scan([path])
            self.assertIn('Office内部構造の不一致', [f.rule for f in report.findings])

    def test_correct_office_container_not_warned(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'letter.docx'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('[Content_Types].xml', '<Types/>')
                z.writestr('word/document.xml', '<w:document/>')
            report = file_inspector.scan([path])
            self.assertNotIn('Office内部構造の不一致', [f.rule for f in report.findings])

    def test_office_external_relationship_whitespace(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'letter.docx'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('[Content_Types].xml', '<Types/>')
                z.writestr('word/document.xml', '<w:document/>')
                z.writestr('word/_rels/document.xml.rels', "<Relationship TargetMode = 'External' Target='https://example.invalid' />")
            report = file_inspector.scan([path])
            self.assertIn('Office外部参照', [f.rule for f in report.findings])

    def test_github_token_assignment_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'settings.env'
            path.write_text('GITHUB_TOKEN=DemoSecret12345678\n', encoding='utf-8')
            report = secret_scout.scan([path])
            self.assertTrue(report.findings)
            self.assertNotIn('DemoSecret12345678', json.dumps(report.export_data(), ensure_ascii=False))

    def test_cardinality_caps_signal_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'access.log'
            lines = []
            for i in range(12):
                lines.append(f'203.0.113.{i+1} - - [08/Nov/2026:01:{i:02d}:02 +0900] "GET /route/{i} HTTP/1.1" 404 3 "-" "A"')
            path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            with patch.object(log_lantern, 'MAX_UNIQUE_ENDPOINTS', 3), patch.object(log_lantern, 'MAX_UNIQUE_SOURCES_PER_MINUTE', 3):
                report = log_lantern.scan([path])
            self.assertEqual(report.metrics['requests'], 12)
            self.assertLessEqual(len(report.metrics['popular_paths']), 3)
            self.assertTrue(report.truncated)
            self.assertTrue(report.errors)
            self.assertTrue(report.metrics['cardinality_limit_hit'])

    def test_cardinality_limits_do_not_mark_normal_logs_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'access.log'
            path.write_text('203.0.113.1 - - [08/Nov/2026:01:03:02 +0900] "GET /index.html HTTP/1.1" 200 120 "-" "Test"\n', encoding='utf-8')
            report = log_lantern.scan([path])
            self.assertFalse(report.truncated)
            self.assertEqual(report.metrics['requests'], 1)


if __name__ == '__main__':
    unittest.main()
