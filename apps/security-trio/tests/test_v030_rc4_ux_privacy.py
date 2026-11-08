"""Windows-side regression checks for rc4 privacy and Office precision."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import file_inspector
import log_lantern
import secret_scout
from common import redact_url

class Rc4PrivacyAndPrecision(unittest.TestCase):
    def test_username_in_route_is_anonymized(self):
        self.assertEqual(redact_url('/api/users/alice/settings'), '/api/users/[REDACTED]/settings')

    def test_short_numeric_customer_id_is_anonymized(self):
        self.assertEqual(redact_url('/customers/24/invoices'), '/customers/[REDACTED]/invoices')

    def test_non_private_route_is_readable(self):
        self.assertEqual(redact_url('/docs/install/windows'), '/docs/install/windows')

    def test_log_json_redacts_user_slug(self):
        with tempfile.TemporaryDirectory() as td:
            name = Path(td) / 'access.log'
            name.write_text('198.51.100.11 - - [08/Nov/2026:12:11:04 +0900] "GET /users/private-name-abc HTTP/1.1" 200 8\n')
            data = log_lantern.scan([name]).export_data()
            self.assertNotIn('private-name-abc', str(data))

    def test_regular_external_hyperlink_not_flagged_as_suspicious(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'document.docx'
            with zipfile.ZipFile(f, 'w') as z:
                z.writestr('[Content_Types].xml', '<Types/>')
                z.writestr('word/document.xml', '<w:document/>')
                z.writestr('word/_rels/document.xml.rels', '<Relationships><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.invalid/" TargetMode="External" /></Relationships>')
            self.assertNotIn('Office外部参照', [x.rule for x in file_inspector.scan([f]).findings])

    def test_external_template_remains_alert(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'document.docx'
            with zipfile.ZipFile(f, 'w') as z:
                z.writestr('[Content_Types].xml', '<Types/>')
                z.writestr('word/document.xml', '<w:document/>')
                z.writestr('word/_rels/document.xml.rels', '<Relationships><Relationship TargetMode="External" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate" Target="https://example.invalid/template.dotm" /></Relationships>')
            self.assertIn('Office外部参照', [x.rule for x in file_inspector.scan([f]).findings])

    def test_zip_parse_failure_marks_scan_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'corrupted.zip'
            f.write_bytes(b'PK\x03\x04BROKEN')
            result = file_inspector.scan([f])
            self.assertTrue(result.truncated)
            self.assertGreater(result.skipped, 0)

    def test_secret_scan_cannot_silently_omit_excess_zip_entries(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'bulk.zip'
            with zipfile.ZipFile(f, 'w') as z:
                for i in range(3):
                    z.writestr(f'{i}.txt', 'abc')
            with patch.object(secret_scout, 'MAX_ZIP_ENTRIES', 2):
                result = secret_scout.scan([f])
            self.assertTrue(result.truncated)
            self.assertGreater(result.skipped, 0)

if __name__ == '__main__':
    unittest.main()
