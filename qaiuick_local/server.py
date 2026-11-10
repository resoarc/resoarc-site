# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Loopback-only local qAIUIck SQLite server (Python standard library).

Intentionally *not* suitable for direct Internet exposure or multiuser hosting.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .storage import APP_ID, SQLiteStore, StoreError

MAX_BODY = 3 * 1024 * 1024
PATH_ID = re.compile(r"^/api/apps/([A-Za-z0-9][A-Za-z0-9_.-]{1,99})(/init|/export)?$")


def build_handler(store, directory, token):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Cache-Control", "no-store")
            # Runs local app modules, never inline code or remote resources.
            self.send_header("Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
            super().end_headers()

        def log_message(self, format, *args):
            if not self.path.startswith("/api/"):
                super().log_message(format, *args)

        def _json(self, status, payload, extra=None):
            data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def _guard(self, api=False, token_required=False):
            host = self.headers.get("Host", "")
            valid_hosts = {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }
            if host not in valid_hosts:
                self._json(403, {"error": "host_forbidden", "message": "Local host only"})
                return False
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + host:
                self._json(403, {"error": "origin_forbidden", "message": "Cross-site origin rejected"})
                return False
            if self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site"):
                self._json(403, {"error": "cross_site", "message": "Cross-site request rejected"})
                return False
            if token_required and not secrets.compare_digest(self.headers.get("X-QAIUIck-Token", ""), token):
                self._json(403, {"error": "token_forbidden", "message": "Session token required"})
                return False
            return True

        def _body(self):
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise StoreError("content_type", "JSON形式で送信してください")
            try:
                size = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                size = -1
            if not 0 < size <= MAX_BODY:
                raise StoreError("body_size", "要求が大きすぎるか空です")
            try:
                value = json.loads(self.rfile.read(size))
            except (UnicodeDecodeError, ValueError):
                raise StoreError("invalid_json", "JSONを解析できません")
            if not isinstance(value, dict):
                raise StoreError("invalid_json", "JSONオブジェクトが必要です")
            return value

        def _api(self, operation):
            if not self._guard(api=True, token_required=True):
                return
            match = PATH_ID.fullmatch(urlsplit(self.path).path)
            if not match:
                self._json(404, {"error": "not_found", "message": "Not found"})
                return
            app_id, suffix = match.groups()
            try:
                if operation == "initialize" and suffix == "/init":
                    body = self._body()
                    response = store.initialize(app_id, body.get("schema"), body.get("sample", []))
                    self._json(200, response)
                elif operation == "update" and suffix is None:
                    body = self._body()
                    response = store.update(app_id, body.get("schema"), body.get("items"), body.get("revision"))
                    self._json(200, response)
                elif operation == "export" and suffix == "/export":
                    contents = store.export_app(app_id)
                    self._json(200, contents, {"Content-Disposition": f'attachment; filename="{app_id}.json"'})
                else:
                    self._json(405, {"error": "method_not_allowed", "message": "Method not allowed"})
            except StoreError as error:
                self._json(error.status, {"error": error.code, "message": error.message})
            except (ValueError, TypeError) as error:
                self._json(422, {"error": "invalid_request", "message": str(error)})
            except Exception:
                # No stack traces or filesystem paths in HTTP responses.
                self.log_error("Internal error in qAIUIck SQLite storage")
                self._json(500, {"error": "internal_error", "message": "Storage operation failed"})

        def do_GET(self):
            pathname = unquote(urlsplit(self.path).path)
            if pathname == "/api/session":
                if not self._guard(api=True):
                    return
                return self._json(200, {"token": token, "mode": "local-sqlite"})
            if pathname.startswith("/api/"):
                return self._api("export")
            if not self._guard():
                return
            parts = Path(pathname).parts
            if any(part.startswith(".") or part in ("data", "backups", "__pycache__")
                   for part in parts if part not in ("/", "")) or re.search(
                       r"\.(db|sqlite3?|sqlite3-wal|sqlite3-shm|bak|env)$", pathname, re.I):
                self.send_error(404)
                return
            return super().do_GET()

        def do_POST(self):
            if urlsplit(self.path).path.startswith("/api/"):
                return self._api("initialize")
            self._json(405, {"error": "method_not_allowed"})

        def do_PUT(self):
            if urlsplit(self.path).path.startswith("/api/"):
                return self._api("update")
            self._json(405, {"error": "method_not_allowed"})

        def do_OPTIONS(self):
            self._json(405, {"error": "method_not_allowed"})

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description="qAIUIck local SQLite server (loopback only)")
    parser.add_argument("--db", default=str(Path.home() / ".qaiuick" / "data.sqlite3"))
    parser.add_argument("--root", default=".", help="Directory containing examples and src/")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error("Static root is not an existing directory")
    db_path = Path(args.db).resolve()
    if db_path == root or root in db_path.parents:
        parser.error("Database must be OUTSIDE the served static directory")
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be between 1024 and 65535")
    storage = SQLiteStore(db_path)
    session = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                 build_handler(storage, root, session))
    print(f"qAIUIck SQLite: http://127.0.0.1:{args.port}/examples/sqlite-inventory/", flush=True)
    print(f"Database: {db_path}", flush=True)
    print("Loopback only. Do not expose this server to public networks.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping qAIUIck", file=sys.stderr)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
