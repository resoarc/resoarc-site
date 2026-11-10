# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""qAIUIck local SQLite: persistence, conflicts, backup/restore and browser safety."""
from __future__ import annotations

import contextlib
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
sys.path.insert(0, str(ROOT))
from qaiuick_local.storage import Conflict, SQLiteStore
from qaiuick_local.server import build_handler
from qaiuick_local.cli import check_schema, export_json, import_json, restore_new
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def sample_spec():
    return json.loads((ROOT / "examples/sqlite-inventory/spec.snapshot.json").read_text("utf-8"))


def sample_rows():
    return [
        {"id": "one", "name": "M3ボルト", "category": "部品", "qty": 48},
        {"id": "two", "name": "USB-Cケーブル", "category": "部品", "qty": 8},
        {"id": "three", "name": "養生テープ", "category": "消耗品", "qty": 6},
    ]


class SQLiteStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = pathlib.Path(self.temp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db)
        self.schema = sample_spec()
        self.app_id = self.schema["id"]

    def test_seed_once_and_revision_conflict(self):
        first = self.store.initialize(self.app_id, self.schema, sample_rows())
        self.assertEqual(first["revision"], 0)
        self.assertEqual(len(first["items"]), 3)
        next_revision = self.store.update(self.app_id, self.schema, [], 0)
        self.assertEqual(next_revision["revision"], 1)
        self.assertEqual(self.store.initialize(self.app_id, self.schema, sample_rows())["items"], [])
        with self.assertRaises(Conflict) as conflict:
            self.store.update(self.app_id, self.schema, sample_rows(), 0)
        self.assertEqual(conflict.exception.code, "stale_revision")
        self.assertEqual(self.store.export_app(self.app_id)["items"], [])

    def test_fail_closed_schema_change_without_data_loss(self):
        self.store.initialize(self.app_id, self.schema, sample_rows())
        changed = json.loads(json.dumps(self.schema))
        changed["version"] += 1
        changed["fields"]["qty"]["min"] = 10
        with self.assertRaises(Conflict) as conflict:
            self.store.initialize(self.app_id, changed, [])
        self.assertEqual(conflict.exception.code, "schema_changed")
        self.assertEqual(len(self.store.export_app(self.app_id)["items"]), 3)
        status, _ = check_schema(self.store, self._write_spec(changed))
        self.assertEqual(status, "BLOCKED")
        status, _ = check_schema(self.store, self._write_spec(self.schema))
        self.assertEqual(status, "COMPATIBLE")

    def _write_spec(self, schema):
        path = pathlib.Path(self.temp.name) / "candidate.json"
        path.write_text(json.dumps(schema), encoding="utf-8")
        return path

    def test_backup_restore_and_json_roundtrip_are_non_destructive(self):
        self.store.initialize(self.app_id, self.schema, sample_rows())
        backup = pathlib.Path(self.temp.name) / "safe" / "backup.sqlite3"
        result = self.store.backup(backup)
        self.assertEqual(result, backup)
        with self.assertRaises(ValueError):
            self.store.backup(backup)
        with sqlite3.connect(backup) as database:
            self.assertEqual(database.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        restored = restore_new(backup, pathlib.Path(self.temp.name) / "new.sqlite3")
        self.assertEqual(SQLiteStore(restored).export_app(self.app_id)["items"], sample_rows())
        data_path = pathlib.Path(self.temp.name) / "export.json"
        _, digest = export_json(self.store, self.app_id, data_path)
        self.assertEqual(hashlib.sha256(data_path.read_bytes()).hexdigest(), digest)
        imported = import_json(pathlib.Path(self.temp.name) / "import.sqlite3", data_path)
        self.assertEqual(SQLiteStore(imported).export_app(self.app_id)["items"], sample_rows())

    def test_validation_and_invalid_updates_cannot_overwrite(self):
        self.store.initialize(self.app_id, self.schema, sample_rows())
        invalid = sample_rows() + [{"id": "dupe", "name": "m3ボルト", "category": "部品", "qty": 2}]
        with self.assertRaises(Exception):
            self.store.update(self.app_id, self.schema, invalid, 0)
        invalid2 = sample_rows() + [{"id": "bad", "name": "Another", "category": "部品", "qty": 1.5}]
        with self.assertRaises(Exception):
            self.store.update(self.app_id, self.schema, invalid2, 0)
        self.assertEqual(self.store.export_app(self.app_id)["revision"], 0)

    def test_distribution_is_reproducible_and_contains_no_database(self):
        archive = SITE / "downloads/qaiuick-v0.6-beta-source.zip"
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(
            archive.with_suffix(".zip.sha256").read_text("ascii").strip(),
            f"{digest}  {archive.name}")
        with ZipFile(archive) as package:
            self.assertIsNone(package.testzip())
            self.assertEqual(len(package.namelist()), 55)
            self.assertFalse(any(name.endswith((".sqlite3", ".db", ".sqlite")) for name in package.namelist()))
            prefix = "qAIUIck-v0.6-beta/"
            for name in ("remote.js", "quick.js", "spec.js", "define.js"):
                self.assertEqual(package.read(prefix + "src/" + name),
                                 (SITE / "assets/qaiuick" / name).read_bytes())


class SQLiteServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = pathlib.Path(self.temp.name)
        self.db = self.work / "db.sqlite3"
        self.store = SQLiteStore(self.db)
        self.web = self.work / "public"
        self.web.mkdir()
        (self.web / "index.html").write_text("<h1>qAIUIck local</h1>", encoding="utf-8")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(
            self.store, self.web, "test-token-secret"))
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def call(self, path, method="GET", body=None, headers=None):
        head = dict(headers or {})
        encoded = json.dumps(body).encode() if body is not None else None
        if body is not None:
            head["Content-Type"] = "application/json"
        req = Request(self.base + path, data=encoded, headers=head, method=method)
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_auth_host_origin_and_stale_update(self):
        schema = sample_spec()
        path = "/api/apps/" + schema["id"]
        status, _ = self.call(path + "/init", "POST", {"schema": schema, "sample": sample_rows()})
        self.assertEqual(status, 403)
        token = {"X-QAIUIck-Token": "test-token-secret"}
        status, out = self.call(path + "/init", "POST", {"schema": schema, "sample": sample_rows()},
                                {**token, "Origin": "http://attacker.invalid"})
        self.assertEqual(status, 403)
        status, out = self.call(path + "/init", "POST", {"schema": schema, "sample": sample_rows()}, token)
        self.assertEqual((status, out["revision"]), (200, 0))
        status, result = self.call(path, "PUT", {"schema": schema, "items": [], "revision": 0}, token)
        self.assertEqual((status, result["revision"]), (200, 1))
        status, result = self.call(path, "PUT", {"schema": schema, "items": sample_rows(), "revision": 0}, token)
        self.assertEqual((status, result["error"]), (409, "stale_revision"))
        status, result = self.call(path + "/export", "GET", headers=token)
        self.assertEqual((status, result["items"]), (200, []))
        status, result = self.call("/api/session", "GET")
        self.assertEqual(status, 200)
        self.assertEqual(result["token"], "test-token-secret")


@unittest.skipUnless(sync_playwright, "Playwright unavailable")
class SQLiteBrowserTest(unittest.TestCase):
    def test_source_bundle_browser_sqlite_persists_and_rejects_stale_tab(self):
        with tempfile.TemporaryDirectory() as work:
            folder = pathlib.Path(work)
            zip_path = SITE / "downloads/qaiuick-v0.6-beta-source.zip"
            with ZipFile(zip_path) as package:
                package.extractall(folder)
            static = folder / "qAIUIck-v0.6-beta"
            db = folder / "separate-db.sqlite3"
            storage = SQLiteStore(db)
            server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(
                storage, static, "browser-test-token"))
            server.daemon_threads = True
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    ctx = browser.new_context(viewport={"width": 390, "height": 844})
                    base = f"http://127.0.0.1:{server.server_port}/examples/sqlite-inventory/"
                    page = ctx.new_page()
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    response = page.goto(base, wait_until="networkidle", timeout=25000)
                    self.assertEqual(response.status, 200)
                    page.wait_for_function('() => document.querySelectorAll(".qs-table tbody tr").length===3',
                                           timeout=6000)
                    self.assertEqual(page.locator("tbody tr").count(), 3)
                    page.locator('input[q-model="draft.name"]').fill("M8ボルト")
                    page.locator('input[q-model="draft.qty"]').fill("12")
                    page.locator('form[q-submit="save"] button').first.click()
                    page.wait_for_function('() => document.querySelectorAll(".qs-table tbody tr").length===4')
                    # A second tab sees committed rows, but retains its own version.
                    other = ctx.new_page()
                    other.goto(base, wait_until="networkidle", timeout=25000)
                    other.wait_for_function('() => document.querySelectorAll(".qs-table tbody tr").length===4')
                    page.reload(wait_until="networkidle")
                    page.wait_for_function('() => document.querySelectorAll(".qs-table tbody tr").length===4')
                    other.locator('button[q-action="remove"]').first.click()
                    other.wait_for_function('() => document.querySelectorAll(".qs-table tbody tr").length===3')
                    page.locator('button[q-action="remove"]').first.click()
                    page.wait_for_function('() => document.querySelector(".q-error").textContent.includes("別のタブ")')
                    self.assertEqual(len(storage.export_app("inventory-local-sqlite")["items"]), 3)
                    self.assertFalse(errors, errors)
                    self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth-window.innerWidth"), 2)
                    ctx.close()
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
