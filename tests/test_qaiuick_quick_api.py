# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Release-level checks for qAIUIck v0.3 Quick API packaging."""
from pathlib import Path
import hashlib
import re
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ARCHIVE = SITE / "downloads/qaiuick-v0.3-beta-source.zip"
PREFIX = "qAIUIck-v0.3-beta/"

class QAIUIckQuickAPITest(unittest.TestCase):
    def test_public_source_archive_and_checksums(self):
        self.assertTrue(ARCHIVE.is_file())
        data = ARCHIVE.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        declared = ARCHIVE.with_suffix(".zip.sha256").read_text("ascii").strip()
        self.assertEqual(declared, f"{sha}  {ARCHIVE.name}")
        with ZipFile(ARCHIVE) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(archive.namelist()), 30)
            self.assertEqual(
                archive.read(PREFIX + "src/quick.js"),
                (SITE / "assets/qaiuick/quick.js").read_bytes()
            )
            self.assertIn(b"quickApp", archive.read(PREFIX + "examples/quick-todo/main.js"))
            self.assertIn(b"Quick API", archive.read(PREFIX + "docs/QUICK_API.md"))
            self.assertIn(b"Permission", archive.read(PREFIX + "LICENSE"))

    def test_quick_api_avoids_dynamic_execution(self):
        source = (SITE / "assets/qaiuick/quick.js").read_text("utf-8")
        for danger in ("eval(", "new Function(", ".innerHTML", "document.write("):
            self.assertNotIn(danger, source)
        for keyword in ("$add", "$remove", "$update", "$reset", "persist", "createApp"):
            self.assertIn(keyword, source)

    def test_live_examples_use_short_facade(self):
        files = [SITE / "assets/qaiuick-beta/demo.js"] + [
            SITE / "assets/qaiuick-beta/examples" / (kind + ".js")
            for kind in ("inventory", "budget", "tickets", "customers")
        ]
        for file in files:
            with self.subTest(file=file.name):
                src=file.read_text("utf-8")
                self.assertIn("quickApp({", src)
                self.assertNotIn("createStore(", src)
                self.assertNotIn("createApp(", src)
                self.assertNotIn("seedOnce(", src)
                self.assertNotIn("app.render()", src)

    def test_legacy_core_remains(self):
        legacy=(SITE / "assets/qaiuick/qaiuick.js").read_text("utf-8")
        self.assertIn("export function createApp(", legacy)
        advanced=(SITE / "assets/qaiuick/store.js").read_text("utf-8")
        self.assertIn("export function createStore(", advanced)

if __name__ == "__main__":
    unittest.main()
