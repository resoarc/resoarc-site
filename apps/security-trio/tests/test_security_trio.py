"""Safety and regression tests; run: python -m unittest discover -s tests -v"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import app
import common
import file_inspector
import log_lantern
import secret_scout


class TempTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, filename, data):
        path = self.folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        return path


class SecretScoutTests(TempTest):
    def test_generic_assignment(self):
        path = self.write("settings.env", "database_password='pQ9M2zA57YhdB1v'\n")
        result = secret_scout.scan([path])
        self.assertTrue(any(f.rule == "機密値を含む設定" for f in result.findings))
        self.assertNotIn("pQ9M2zA57YhdB1v", json.dumps(result.export_data()))

    def test_private_key_header(self):
        result = secret_scout.scan([self.write("id.pem", "-----BEGIN " + "PRIVATE KEY-----\n(not a real key)\n")])
        self.assertTrue(any(f.severity == "高" for f in result.findings))

    def test_github_token(self):
        token = "ghp_" + "AbCdefGhIjKlMnOpQrStUvWxYz123456"
        result = secret_scout.scan([self.write("config.txt", "TOKEN=" + token)])
        self.assertTrue(any(f.rule == "GitHubトークン形式" for f in result.findings))
        self.assertNotIn(token, json.dumps(result.export_data()))

    def test_aws_key_id(self):
        result = secret_scout.scan([self.write("cfg.txt", "AKIA" + "A1B2C3D4E5F6G7H8")])
        self.assertTrue(any(f.rule == "AWSアクセスキーID形式" for f in result.findings))

    def test_realistic_placeholder_ignored(self):
        result = secret_scout.scan([self.write("example.env", "PASSWORD=YOUR_PASSWORD_HERE\napi_key=change_me_now\n")])
        self.assertFalse(result.findings)

    def test_short_value_not_flagged(self):
        result = secret_scout.scan([self.write("sample.env", "password=short\n")])
        self.assertFalse(result.findings)

    def test_binary_skipped(self):
        result = secret_scout.scan([self.write("private.pem", b"\x00\x01password=abcdefghijk")])
        self.assertFalse(result.findings)
        self.assertGreaterEqual(result.skipped, 1)

    def test_zip_secret_scanned_without_extraction(self):
        path = self.folder / "src.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("configs/prod.env", "password=sJ3KlN7mXq12F4v9")
        result = secret_scout.scan([path])
        self.assertTrue(any("prod.env" in f.target for f in result.findings))
        self.assertFalse((self.folder / "configs").exists())

    def test_zip_traversal_detected_without_extraction(self):
        path = self.folder / "out.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("../bad.env", "password=Zx7Yq42AbCdEfGhI")
        result = secret_scout.scan([path])
        self.assertTrue(any(f.rule == "ZIP内の危険なパス" for f in result.findings))
        self.assertFalse((self.folder.parent / "bad.env").exists())

    def test_zip_member_limit(self):
        path = self.folder / "large.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("oversized.env", "A" * (secret_scout.MAX_MEMBER + 5))
        result = secret_scout.scan([path])
        self.assertGreaterEqual(result.skipped, 1)

    def test_zip_malformed(self):
        result = secret_scout.scan([self.write("broken.zip", b"PK\x03\x04invalid")])
        self.assertTrue(result.errors)

    def test_secret_url_with_password(self):
        text = "REDIS_URL=redis://alice:azBY0Zcvb8nQx62u@localhost:6379"
        result = secret_scout.scan([self.write("backend.env", text)])
        self.assertTrue(any(f.rule == "認証情報付き接続URI" for f in result.findings))
        self.assertNotIn("azBY0Zcv", json.dumps(result.export_data()))

    def test_unknown_extension(self):
        result = secret_scout.scan([self.write("image.png", b"password=Zxcv123456789ABCDE")])
        self.assertFalse(result.findings)
        self.assertGreaterEqual(result.skipped, 1)

    def test_symlink_skipped(self):
        target = self.write("secret.env", "password=Zxcv123456789ABCDE")
        link = self.folder / "alias.env"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink not supported")
        result = secret_scout.scan([link])
        self.assertEqual(result.scanned, 0)

    def test_cancelled(self):
        cancelled = threading.Event()
        cancelled.set()
        result = secret_scout.scan([self.folder], cancel=cancelled)
        self.assertEqual(result.scanned, 0)
        self.assertTrue(result.metrics["cancelled"])


class LogLanternTests(TempTest):
    LINE = '198.51.100.34 - - [08/Nov/2026:01:00:05 +0900] "GET /health HTTP/1.1" 200 100 "-" "test"\n'

    def test_combined_basic(self):
        out = log_lantern.scan([self.write("access.log", self.LINE)])
        self.assertEqual(out.metrics["requests"], 1)
        self.assertEqual(out.metrics["status_codes"]["200"], 1)
        self.assertFalse(out.findings)

    def test_nginx_and_query_redaction(self):
        log = self.LINE.replace("/health", "/health?access_token=ultra_private_value")
        out = log_lantern.scan([self.write("nginx.log", log)])
        data = json.dumps(out.export_data())
        self.assertNotIn("ultra_private_value", data)
        self.assertNotIn("198.51.100.34", data)
        self.assertEqual(out.metrics["popular_paths"][0]["path"], "/health")

    def test_iis_w3c(self):
        text = "#Software: Microsoft IIS\n#Fields: date time s-ip c-ip cs-method cs-uri-stem sc-status\n2026-11-08 01:01:01 10.0.0.1 203.0.113.20 GET /index.html 200\n"
        out = log_lantern.scan([self.write("iis.log", text)])
        self.assertEqual(out.metrics["requests"], 1)
        self.assertNotIn("203.0.113.20", json.dumps(out.export_data()))

    def test_dotenv_detection(self):
        out = log_lantern.scan([self.write("access.log", self.LINE.replace("/health", "/.env"))])
        self.assertTrue(any("秘密" in f.rule for f in out.findings))

    def test_traversal_detection(self):
        out = log_lantern.scan([self.write("access.log", self.LINE.replace("/health", "/%2e%2e/%2e%2e/private"))])
        self.assertTrue(any("移動" in f.rule for f in out.findings))

    def test_sqli_detection(self):
        out = log_lantern.scan([self.write("access.log", self.LINE.replace("/health", "/x?filter=union%20select%20password"))])
        self.assertTrue(any("SQL" in f.rule for f in out.findings))
        self.assertNotIn("password", json.dumps(out.export_data()))

    def test_burst_detection(self):
        out = log_lantern.scan([self.write("access.log", self.LINE * 85)])
        self.assertTrue(any("集中" in f.rule for f in out.findings))

    def test_auth_fail_detection(self):
        out = log_lantern.scan([self.write("access.log", self.LINE.replace(" 200 ", " 403 ") * 12)])
        self.assertTrue(any("認証" in f.rule for f in out.findings))

    def test_404_many_distinct_paths(self):
        lines = "".join(self.LINE.replace("/health", f"/gone{i}").replace(" 200 ", " 404 ") for i in range(13))
        out = log_lantern.scan([self.write("access.log", lines)])
        self.assertTrue(any("404" in f.rule for f in out.findings))

    def test_malformed(self):
        out = log_lantern.scan([self.write("access.log", "junk\n" + self.LINE)])
        self.assertEqual(out.metrics["unparsed_lines"], 1)
        self.assertTrue(any("解析" in f.rule for f in out.findings))

    def test_bad_format_returns_error(self):
        out = log_lantern.scan([self.write("access.log", "nonsense\n")])
        self.assertTrue(out.errors)

    def test_absolute_url_userinfo_not_leaked(self):
        log = self.LINE.replace("/health", "https://user:" + "password@example.invalid/health?x=secret")
        out = log_lantern.scan([self.write("access.log", log)])
        self.assertNotIn("user:password", json.dumps(out.export_data()))
        self.assertNotIn("x=secret", json.dumps(out.export_data()))


class InspectorTests(TempTest):
    def test_magic(self):
        self.assertEqual(file_inspector.file_type(b"%PDF-1.4"), "PDF")
        self.assertEqual(file_inspector.file_type(file_inspector.LNK_HEADER), "LNK")
        self.assertEqual(file_inspector.file_type(b"\x89PNG\r\n\x1a\n"), "PNG")
        self.assertEqual(file_inspector.file_type(b"\xff\xd8\xff"), "JPEG")

    def test_pdf_script_marker(self):
        out = file_inspector.scan([self.write("invoice.pdf", b"%PDF-1.7\n/JavaScript /OpenAction")])
        self.assertTrue(any("PDF" in f.rule for f in out.findings))

    def test_lnk_command(self):
        out = file_inspector.scan([self.write("sample.lnk", file_inspector.LNK_HEADER + "powershell".encode("utf-16le"))])
        self.assertTrue(any("LNK" in f.rule for f in out.findings))

    def test_lnk_mismatch(self):
        out = file_inspector.scan([self.write("picture.png", file_inspector.LNK_HEADER + b"x")])
        self.assertTrue(any("偽装" in f.rule for f in out.findings))

    def test_double_extension(self):
        out = file_inspector.scan([self.write("statement.pdf.exe", b"untrusted inert sample")])
        self.assertTrue(any("二重" in f.rule for f in out.findings))

    def test_pe_disguised_pdf(self):
        data = bytearray(160)
        data[:2] = b"MZ"
        data[0x3c:0x40] = (128).to_bytes(4, "little")
        data[128:132] = b"PE\0\0"
        out = file_inspector.scan([self.write("attachment.pdf", bytes(data))])
        self.assertTrue(any("不一致" in f.rule for f in out.findings))

    def test_macro_in_office(self):
        path = self.folder / "attachment.docm"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/vbaProject.bin", b"test-only")
        out = file_inspector.scan([path])
        self.assertTrue(any("VBA" in f.rule for f in out.findings))

    def test_external_relationship(self):
        path = self.folder / "attachment.docx"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/_rels/document.xml.rels", '<Relationship TargetMode="External" Target="https://example.invalid"/>')
        out = file_inspector.scan([path])
        self.assertTrue(any("外部参照" in f.rule for f in out.findings))

    def test_archive_traversal(self):
        path = self.folder / "malformed.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("../../escape.txt", "safe sample")
        out = file_inspector.scan([path])
        self.assertTrue(any("危険なパス" in f.rule for f in out.findings))

    def test_hash(self):
        body = b"test-body"
        out = file_inspector.scan([self.write("file.bin", body)])
        self.assertEqual(out.metrics["files"][0]["sha256"], hashlib.sha256(body).hexdigest())

    def test_plain_file_not_malware(self):
        out = file_inspector.scan([self.write("hello.txt", "normal text")])
        self.assertFalse(out.findings)

    def test_script_type_is_info_only(self):
        out = file_inspector.scan([self.write("calc.bat", "echo hello")])
        self.assertTrue(any(f.severity == "情報" for f in out.findings))
        self.assertFalse(any(f.severity == "高" for f in out.findings))

    def test_unicode_bidi_warning(self):
        out = file_inspector.scan([self.write("file\u202egnp.exe", "content")])
        self.assertTrue(any("文字方向" in f.rule for f in out.findings))

    def test_motw_mock(self):
        with patch.object(file_inspector, "_mark_of_web", return_value=3):
            out = file_inspector.scan([self.write("web.pdf", b"%PDF-1.4")])
        self.assertTrue(any("インターネット" in f.rule for f in out.findings))


class CommonAndCLITests(TempTest):
    def test_ip_v4(self):
        self.assertEqual(common.mask_ip("198.51.100.34"), "198.51.x.x")

    def test_ip_v6(self):
        self.assertNotIn("2001:db8::abcd", common.mask_ip("2001:db8::abcd"))

    def test_ip_bad_hostname(self):
        self.assertTrue(common.mask_ip("attacker.invalid").startswith("host-"))

    def test_csv_formula_injection(self):
        r = common.ScanResult("Demo")
        r.add(common.Finding("中", "rule", "=HYPERLINK(\"https://evil\")", "safe"))
        path = self.folder / "report.csv"
        common.export_csv(path, r)
        self.assertIn("'=HYPERLINK", path.read_text(encoding="utf-8-sig"))

    def test_json_atomic(self):
        r = common.ScanResult("Demo")
        path = self.folder / "report.json"
        common.export_json(path, r)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["tool"], "Demo")

    def test_cli_exit_clear(self):
        path = self.write("clean.env", "password=YOUR_PASSWORD_HERE")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_cli("secret", [str(path)], None, "json"), 0)

    def test_cli_exit_findings(self):
        path = self.write("bad.env", "password=ZxvBca7WxPv9T5mQ")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_cli("secret", [str(path)], None, "json"), 1)

    def test_cli_exit_missing(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_cli("secret", [str(self.folder / "missing")], None, "json"), 2)

    def test_cli_report(self):
        path = self.write("sample.log", log_lantern_tests_line())
        output = self.folder / "report.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(app.run_cli("log", [str(path)], str(output), "json"), 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["tool"], "ResoArc Log Lantern")

    def test_samples(self):
        paths = app.build_samples("secret", self.folder)
        self.assertTrue(secret_scout.scan(paths).findings)
        logpaths = app.build_samples("log", self.folder)
        self.assertGreater(log_lantern.scan(logpaths).metrics["requests"], 0)
        inspected = app.build_samples("file", self.folder)
        self.assertTrue(file_inspector.scan(inspected).findings)


def log_lantern_tests_line():
    return '203.0.113.22 - - [08/Nov/2026:01:00:05 +0900] "GET /health HTTP/1.1" 200 100 "-" "client"\n'


class EdgeCases(TempTest):
    def test_safe_filename_token_redaction(self):
        token = "ghp_" + "AbCdefGhIjKlMnOpQrStUvWxYz123456"
        self.assertNotIn(token, common.safe_name("prefix_" + token))

    def test_safe_filename_bidi(self):
        self.assertIn("[BIDI]", common.safe_name("sample\u202eexe.pdf"))

    def test_walk_files_skips_git(self):
        self.write(".git/config.env", "password=XyZf9Rg4kPbc28Wq")
        paths = list(common.walk_files([self.folder], limit=100))
        self.assertFalse(any(".git" in p.parts for p in paths))

    def test_scanner_over_text_cap(self):
        path = self.folder / "huge.env"
        with path.open("wb") as f:
            f.truncate(secret_scout.MAX_TEXT + 1)
        out = secret_scout.scan([path])
        self.assertEqual(out.scanned, 0)
        self.assertGreaterEqual(out.skipped, 1)

    def test_nested_zip_ignored(self):
        path = self.folder / "outer.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("inside.zip", b"PK\x03\x04invalid")
        out = secret_scout.scan([path])
        self.assertGreaterEqual(out.skipped, 1)
        self.assertFalse(out.findings)

    def test_unsupported_log_extension_ignored(self):
        path = self.write("input.csv", "fake data")
        out = log_lantern.scan([path])
        self.assertEqual(out.scanned, 0)
        self.assertTrue(out.errors)

    def test_log_oversized_file_ignored(self):
        path = self.folder / "oversized.log"
        with path.open("wb") as f:
            f.truncate(log_lantern.MAX_FILE_SIZE + 1)
        out = log_lantern.scan([path])
        self.assertGreaterEqual(out.skipped, 1)
        self.assertTrue(out.errors)

    def test_log_cancelled(self):
        event = threading.Event()
        event.set()
        out = log_lantern.scan([self.write("test.log", LogLanternTests.LINE)], cancel=event)
        self.assertEqual(out.scanned, 0)
        self.assertTrue(out.metrics["cancelled"])

    def test_ole_legacy_warning(self):
        path = self.write("report.doc", file_inspector.OLE_HEADER + b"x" * 80)
        out = file_inspector.scan([path])
        self.assertTrue(any("OLE" in f.rule for f in out.findings))

    def test_ole_docx_mismatch(self):
        path = self.write("report.docx", file_inspector.OLE_HEADER + b"x" * 80)
        out = file_inspector.scan([path])
        self.assertTrue(any("不一致" in f.rule for f in out.findings))

    def test_pe_pdf_polyglot_prioritizes_executable(self):
        data = bytearray(700)
        data[0:2] = b"MZ"
        data[0x3c:0x40] = (128).to_bytes(4, "little")
        data[128:132] = b"PE\0\0"
        data[300:308] = b"%PDF-1.4"
        self.assertEqual(file_inspector.file_type(bytes(data)), "PE")

    def test_file_zip_expansion_warning(self):
        path = self.folder / "giant.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("big.txt", b"A" * (23 * 1024 * 1024))
        out = file_inspector.scan([path])
        self.assertTrue(any("容量膨張" in f.rule for f in out.findings))

    def test_file_cancelled(self):
        event = threading.Event()
        event.set()
        out = file_inspector.scan([self.write("test.pdf", b"%PDF-1.4")], cancel=event)
        self.assertEqual(out.scanned, 0)
        self.assertTrue(out.metrics["cancelled"])


    def test_secret_input_limit_is_explicit(self):
        path = self.write("tiny.env", "# benign")
        with patch.object(secret_scout, "walk_files", return_value=iter([path] * 3001)):
            out = secret_scout.scan([path])
        self.assertTrue(out.truncated)
        self.assertTrue(any("上限" in e for e in out.errors))

    def test_log_input_limit_is_explicit(self):
        path = self.write("tiny.log", LogLanternTests.LINE)
        with patch.object(log_lantern, "walk_files", return_value=iter([path] * 51)):
            out = log_lantern.scan([path])
        self.assertTrue(out.truncated)

    def test_file_input_limit_is_explicit(self):
        path = self.write("tiny.bin", b"abc")
        with patch.object(file_inspector, "walk_files", return_value=iter([path] * 501)):
            out = file_inspector.scan([path])
        self.assertTrue(out.truncated)

    def test_cli_truncated_returns_error(self):
        fake = common.ScanResult("fake")
        fake.scanned = 1
        fake.truncated = True
        with patch.dict(app.TOOLS, {"secret": ("Secret Scout", "", "", lambda paths: fake)}):
            with contextlib.redirect_stdout(io.StringIO()):
                status = app.run_cli("secret", ["dummy"], None, "json")
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
