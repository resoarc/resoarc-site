# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""Regression checks for the permission boundaries in developer-preview workflows."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ".github/workflows/resoarcos-pc-v0.1.1-dev.yml",
    ".github/workflows/resoarcos-preview-release.yml",
)

class ReleaseWorkflowSecurityTests(unittest.TestCase):
    def test_publish_is_separate_from_read_only_build(self):
        for name in WORKFLOWS:
            with self.subTest(workflow=name):
                data = (ROOT / name).read_text(encoding="utf-8")
                self.assertRegex(data, r"(?m)^permissions:\n  contents: read$")
                self.assertNotRegex(data, r"(?m)^  contents: write$")
                self.assertIn("  build-verify:\n", data)
                self.assertIn("  publish:\n", data)
                build = data.split("  build-verify:\n", 1)[1].split("  publish:\n", 1)[0]
                publish = data.split("  publish:\n", 1)[1]
                self.assertIn("permissions:\n      contents: read", build)
                self.assertNotIn("contents: write", build)
                self.assertIn("permissions:\n      contents: write", publish)
                self.assertIn("needs: build-verify", publish)
                self.assertIn("github.event_name == 'workflow_dispatch'", publish)
                self.assertNotIn("\n  push:\n", data)
                self.assertIn("persist-credentials: false", build)
                self.assertNotIn("gh release create", build)
                self.assertIn("sha256sum --check release/SHA256SUMS", publish)
                self.assertIn("Refusing to overwrite existing immutable tag", publish)
                self.assertIn("source.zip", build)
                self.assertRegex(data, r"(?m)^\s*uses: actions/download-artifact@[a-f0-9]{40}\s+#")
                self.assertRegex(data, r"(?m)^\s*uses: actions/upload-artifact@[a-f0-9]{40}\s+#")
                for line in data.splitlines():
                    if re.match(r"\s*uses:\s*", line):
                        self.assertRegex(line, r"uses:\s+[^@\s]+@[a-f0-9]{40}(?:\s|$)")
    
if __name__ == "__main__":
    unittest.main()
