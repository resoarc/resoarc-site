"""Preflight must reject hostile archives before eager ZIP directory materialization."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import file_inspector
import secret_scout
from common import zip_preflight


class ArchivePreflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _zip(self, name, count):
        p = self.root / name
        with zipfile.ZipFile(p, 'w') as z:
            for i in range(count):
                z.writestr(f'item{i:04d}.txt', '')
        return p

    def test_fast_reject_when_secret_archive_has_too_many_entries(self):
        p = self._zip('large.zip', 2001)
        with patch.object(secret_scout.zipfile, 'ZipFile', side_effect=AssertionError('must reject before ZipFile')):
            result = secret_scout.scan([p])
        self.assertTrue(result.truncated)
        self.assertGreater(result.skipped, 0)

    def test_fast_reject_when_file_archive_has_too_many_entries(self):
        p = self._zip('large.zip', 2501)
        with patch.object(file_inspector.zipfile, 'ZipFile', side_effect=AssertionError('must reject before ZipFile')):
            result = file_inspector.scan([p])
        self.assertTrue(result.truncated)
        self.assertGreater(result.skipped, 0)
        self.assertTrue(any('ZIP項目数が過大' in f.rule for f in result.findings))

    def test_central_directory_size_cap(self):
        p = self._zip('small.zip', 2)
        self.assertIsNotNone(zip_preflight(p, max_entries=2000, max_directory_bytes=1))

    def test_tiny_valid_zip_not_rejected(self):
        p = self._zip('small.zip', 2)
        self.assertIsNone(zip_preflight(p, max_entries=2000))

    def test_signature_inside_zip_comment_is_not_eocd(self):
        path = self.root / 'has-comment.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('good.txt', 'hello')
            z.comment = b'comments: ' + b'PK\x05\x06' + (b'\xff' * 30)
        self.assertIsNone(zip_preflight(path, max_entries=2000))
        # Python's zipfile itself rejects this unusual comment, which must
        # become an incomplete scan rather than a false clean result.
        self.assertTrue(secret_scout.scan([path]).errors)

    def test_broken_zip_is_not_claimed_clean(self):
        p = self.root / 'broken.zip'
        p.write_bytes(b'PK\x03\x04' + b'0' * 20)
        self.assertIsNone(zip_preflight(p, max_entries=2000))
        result = secret_scout.scan([p])
        self.assertTrue(result.errors)


if __name__ == '__main__':
    unittest.main()
