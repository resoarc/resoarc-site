"""Regression tests for strict, fail-closed GitHub Release mirror retries."""
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_external_archive_mirror as mirror  # noqa: E402


def http_error(status):
    return urllib.error.HTTPError("https://api.github.com/example", status, "temporary", {}, None)


class ReleaseMirrorRetryTests(unittest.TestCase):
    def test_transient_504_retries_and_returns_json(self):
        response = io.BytesIO(b'{"draft": false, "assets": []}')
        with mock.patch.object(mirror.urllib.request, "urlopen", side_effect=[http_error(504), response]) as opener, \
             mock.patch.object(mirror.time, "sleep") as sleeper:
            result = mirror.fetch_json("https://api.github.com/example")
        self.assertEqual(result["draft"], False)
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(1)

    def test_terminal_504_fails_after_bounded_retries(self):
        with mock.patch.object(mirror.urllib.request, "urlopen", side_effect=[http_error(504)] * 3) as opener, \
             mock.patch.object(mirror.time, "sleep") as sleeper:
            with self.assertRaises(urllib.error.HTTPError):
                mirror.fetch_json("https://api.github.com/example")
        self.assertEqual(opener.call_count, 3)
        self.assertEqual([c.args[0] for c in sleeper.call_args_list], [1, 2])

    def test_404_never_retries(self):
        with mock.patch.object(mirror.urllib.request, "urlopen", side_effect=http_error(404)) as opener, \
             mock.patch.object(mirror.time, "sleep") as sleeper:
            with self.assertRaises(urllib.error.HTTPError):
                mirror.fetch_json("https://api.github.com/example")
        self.assertEqual(opener.call_count, 1)
        sleeper.assert_not_called()

    def test_504_fallback_verifies_all_pinned_assets(self):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit.json"
            rows = [{"filename": f"archive-{i}.zip", "bytes": 3, "sha256": "a"*64} for i in range(20)]
            audit.write_text(json.dumps({"assets": rows}), encoding="utf-8")
            with mock.patch.object(mirror, "AUDIT", audit), \
                 mock.patch.object(mirror, "mirror_map", side_effect=http_error(504)), \
                 mock.patch.object(mirror, "check_direct_release") as direct:
                mirror.main(True)
                direct.assert_called_once_with(rows, True)

    def test_404_does_not_allow_api_bypass(self):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit.json"
            rows = [{"filename": f"archive-{i}.zip", "bytes": 3, "sha256": "a"*64} for i in range(20)]
            audit.write_text(json.dumps({"assets": rows}), encoding="utf-8")
            with mock.patch.object(mirror, "AUDIT", audit), \
                 mock.patch.object(mirror, "mirror_map", side_effect=http_error(404)), \
                 mock.patch.object(mirror, "check_direct_release") as direct:
                with self.assertRaises(urllib.error.HTTPError):
                    mirror.main(True)
                direct.assert_not_called()

    def test_504_fallback_does_not_ignore_digest_failure(self):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit.json"
            rows = [{"filename": f"archive-{i}.zip", "bytes": 3, "sha256": "a"*64} for i in range(20)]
            audit.write_text(json.dumps({"assets": rows}), encoding="utf-8")
            with mock.patch.object(mirror, "AUDIT", audit), \
                 mock.patch.object(mirror, "mirror_map", side_effect=http_error(504)), \
                 mock.patch.object(mirror, "check_direct_release", side_effect=ValueError("digest mismatch")):
                with self.assertRaisesRegex(ValueError, "digest mismatch"):
                    mirror.main(True)


if __name__ == "__main__":
    unittest.main()
