"""Fail-closed security regression tests for Office relationship ZIP metadata.

Large, unreadable or encrypted relationships must never be silently treated as
proof of absence of external references. Input files are synthetic.
"""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import file_inspector


class RelationshipSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "example.docx"

    def make_document(self, relationships):
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
            for i, payload in enumerate(relationships):
                archive.writestr(f"word/_rels/relationship{i}.rels", payload)
        return self.path

    def scan(self):
        return file_inspector.scan([self.path])

    def test_large_rels_is_visible_as_incomplete(self):
        self.make_document(["A" * (file_inspector.MAX_RELS_BYTES + 1)])
        result = self.scan()
        self.assertTrue(result.truncated)
        self.assertGreaterEqual(result.skipped, 1)
        self.assertIn("Office関係定義の未検査", [f.rule for f in result.findings])

    def test_aggregate_rels_budget_is_visible_as_incomplete(self):
        self.make_document(["<Relationships/>", "<Relationships/>", "<Relationships/>"])
        with patch.object(file_inspector, "MAX_RELS_TOTAL", 20):
            result = self.scan()
        self.assertTrue(result.truncated)
        self.assertGreaterEqual(result.skipped, 1)
        self.assertIn("Office関係定義の未検査", [f.rule for f in result.findings])

    def test_external_template_flag_survives_later_oversized_rels(self):
        template = (
            '<Relationship Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/attachedTemplate" '
            'TargetMode="External" Target="https://example.invalid/template.dotm" />'
        )
        self.make_document([template, "B" * (file_inspector.MAX_RELS_BYTES + 1)])
        result = self.scan()
        self.assertIn("Office外部参照", [f.rule for f in result.findings])
        self.assertIn("Office関係定義の未検査", [f.rule for f in result.findings])
        self.assertTrue(result.truncated)

    def test_only_external_hyperlink_does_not_create_security_finding(self):
        hyperlink = (
            '<Relationship Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/hyperlink" '
            'TargetMode="External" Target="https://example.invalid/" />'
        )
        self.make_document([hyperlink])
        result = self.scan()
        self.assertFalse(result.truncated)
        self.assertFalse(any(f.rule in ("Office外部参照", "Office関係定義の未検査") for f in result.findings))

    def test_normal_external_template_without_gaps_is_detected(self):
        template = '<Relationship TargetMode = "External" Type="template" Target="https://example.invalid/"/>'
        self.make_document([template])
        result = self.scan()
        self.assertIn("Office外部参照", [f.rule for f in result.findings])
        self.assertFalse(result.truncated)


if __name__ == "__main__":
    unittest.main()
