"""Regression tests for the immutable ResoArcOS source archive check."""
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

script = Path(__file__).resolve().parents[1] / "scripts/verify_resoarcos_snapshot.py"
spec = importlib.util.spec_from_file_location("resoarcos_snapshot", script)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SourceSnapshotTests(unittest.TestCase):
    def test_current_tracked_source_passes(self):
        digest, count = audit.check()
        self.assertEqual(digest, audit.EXPECTED)
        self.assertGreater(count, 20)

    def test_digest_mismatch_fails_before_extracting(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "source.zip"
            bad.write_bytes(b"not a zip archive")
            with patch.object(audit, "ARCHIVE", bad):
                with self.assertRaisesRegex(ValueError, "digest mismatch"):
                    audit.check()

    def test_rejects_path_traversal_even_with_matching_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "source.zip"
            with ZipFile(bad, "w", ZIP_DEFLATED) as z:
                z.writestr("../escaped.txt", b"unsafe")
            from hashlib import sha256
            with patch.object(audit, "ARCHIVE", bad), patch.object(audit, "EXPECTED", sha256(bad.read_bytes()).hexdigest()):
                with self.assertRaisesRegex(ValueError, "Unsafe ZIP pathname"):
                    audit.check()


if __name__ == "__main__":
    unittest.main()
