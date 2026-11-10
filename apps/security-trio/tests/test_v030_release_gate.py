"""v0.3 security/completeness regression tests (synthetic data, no network)."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

import app
import common
import file_inspector
import log_lantern
import secret_scout


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='resoarc-rc-')
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, content):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
        return p

    def zip(self, name='bundle.zip', files=None):
        p = self.root / name
        with zipfile.ZipFile(p, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for filename, value in (files or {'note.txt': b'example content'}).items():
                archive.writestr(filename, value)
        return p

    def test_no_overwrite_existing_inside_input_folder(self):
        p = self.put('inputs/report.json', b'existing bytes')
        self.assertTrue(common.output_overwrites_input(p, [p.parent]))

    def test_allow_new_report_in_input_folder(self):
        p = self.put('inputs/demo.txt', b'hello')
        self.assertFalse(common.output_overwrites_input(p.parent / 'new-report.json', [p.parent]))

    def test_no_overwrite_hardlink_input(self):
        p = self.put('original.json', b'secret')
        alias = self.root / 'linked.json'
        os.link(p, alias)
        self.assertTrue(common.output_overwrites_input(alias, [p]))

    def test_no_overwrite_input_folder_from_cli(self):
        p = self.put('inputs/report.json', 'password=strongABCabc123')
        with contextlib.redirect_stderr(io.StringIO()):
            code = app.run_cli('secret', [str(p.parent)], str(p), 'json')
        self.assertEqual(code, 2)
        self.assertEqual(p.read_text(), 'password=strongABCabc123')

    def test_filename_contains_secret_kv_is_masked(self):
        self.assertNotIn('SeCrEtValue99', common.safe_name('backup_token=SeCrEtValue99.zip'))

    def test_zip_executable_metadata_detected(self):
        p = self.zip(files={'work/readme.txt': b'hello', 'work/payload.ps1': b'# inert'})
        res = file_inspector.scan([p])
        self.assertTrue(any(x.rule == 'ZIP内に実行可能な形式' for x in res.findings))
        self.assertFalse(res.truncated)
        self.assertEqual(res.skipped, 0)

    def test_zip_2501_entry_limit_marked_incomplete(self):
        p = self.root / 'large-directory.zip'
        with zipfile.ZipFile(p, 'w', compression=zipfile.ZIP_STORED) as z:
            for i in range(2501):
                z.writestr('item_%04d.txt' % i, '')
        r = file_inspector.scan([p])
        self.assertTrue(r.truncated)
        self.assertGreater(r.skipped, 0)
        self.assertTrue(any('項目数が過大' in f.rule for f in r.findings))

    def test_zip_encrypted_flag_is_incomplete(self):
        p = self.zip(files={'private.txt': b'hello'})
        data = bytearray(p.read_bytes())
        # Test metadata handling without generating an actual encrypted payload.
        local = data.index(b'PK\x03\x04')
        central = data.index(b'PK\x01\x02')
        for offset in (local + 6, central + 8):
            flags = int.from_bytes(data[offset:offset+2], 'little') | 0x1
            data[offset:offset+2] = flags.to_bytes(2, 'little')
        p.write_bytes(data)
        r = file_inspector.scan([p])
        self.assertGreater(r.skipped, 0)
        self.assertTrue(any('暗号化' in f.rule for f in r.findings))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_cli('file', [str(p)], None, 'json'), 2)

    def test_secret_unsafe_archive_path_incomplete(self):
        p = self.zip(files={'../outside.txt': b'harmless data'})
        r = secret_scout.scan([p])
        self.assertGreater(r.skipped, 0)
        self.assertTrue(any('危険なパス' in f.rule for f in r.findings))

    def test_double_encoded_log_probe(self):
        line = ('203.0.113.24 - - [08/Nov/2026:01:03:03 +0900] '
                '"GET /admin/%252e%252e%252fetc%252fpasswd HTTP/1.1" 404 0\n')
        p = self.put('access.log', line)
        r = log_lantern.scan([p])
        self.assertTrue(any('ディレクトリ移動' in f.rule for f in r.findings))
        self.assertNotIn('203.0.113.24', json.dumps(r.export_data(), ensure_ascii=False))

    def test_zip_never_extracts_executable(self):
        p = self.zip(files={'launcher.exe': b'MZ\0\0' + b'none' * 20})
        file_inspector.scan([p])
        self.assertFalse((self.root / 'launcher.exe').exists())

    def test_clean_zip_still_clean(self):
        p = self.zip(files={'document.txt': b'nothing dangerous'})
        r = file_inspector.scan([p])
        self.assertEqual(len(r.findings), 0)
        self.assertEqual(r.skipped, 0)


if __name__ == '__main__':
    unittest.main()
