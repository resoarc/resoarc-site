# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Offline-safe qAIUIck backup, restore, JSON export/import, and schema preflight."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from .storage import APP_ID, SQLiteStore, StoreError, stable_json, utc_now


def must_not_exist(output):
    path = Path(output).resolve()
    if path.exists():
        raise ValueError(f"Destination already exists (will not overwrite): {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_json(store, app_id, output):
    path = must_not_exist(output)
    payload = store.export_app(app_id)
    result = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    # Created with exclusive mode; no overwrite even across concurrent processes.
    with path.open("xb") as stream:
        stream.write(result)
    return path, hashlib.sha256(result).hexdigest()


def import_json(output, source):
    path = must_not_exist(output)
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != "qaiuick-sqlite-export-v1":
        raise ValueError("Not a qAIUIck SQLite JSON export")
    if not isinstance(data.get("fields"), dict):
        raise ValueError("Missing field definitions")
    schema = {
        "id": data["id"], "version": data["version"],
        "fields": data["fields"],
    }
    store = SQLiteStore(path)
    try:
        # Check and write all records before completing the import.
        store.initialize(data["id"], schema, data["items"])
        with store.connect() as db:
            integrity = db.execute("PRAGMA quick_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError("Database integrity verification failed")
    except BaseException:
        for suffix in ("", "-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)
        raise
    return path


def check_schema(store, source):
    schema = json.loads(Path(source).read_text(encoding="utf-8"))
    app_id, version, fields = SQLiteStore.schema_shape(schema)
    with store.connect() as db:
        current = db.execute("SELECT * FROM apps WHERE app_id=?", (app_id,)).fetchone()
        if current is None:
            return "NEW_APP", "No saved app for " + app_id
        shape = json.loads(current["fields_json"])
        if stable_json(shape) != stable_json(fields):
            new = {k: fields.get(k) for k in set(fields) | set(shape) if fields.get(k) != shape.get(k)}
            return "BLOCKED", "Field schema differs (backup and reviewed migration required): " + ", ".join(sorted(new))
        if version < current["schema_version"]:
            return "BLOCKED", "Specification version is older than saved version"
        return "COMPATIBLE", f"Schema unchanged. Saved revision {current['revision']}."


def check_integrity(db_path):
    if not Path(db_path).is_file():
        raise ValueError("Database does not exist")
    with sqlite3.connect(str(db_path)) as db:
        result = db.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError("SQLite integrity_check failed: " + result)
    return True


def restore_new(source, output):
    check_integrity(source)
    path = must_not_exist(output)
    try:
        with sqlite3.connect(str(source)) as src, sqlite3.connect(str(path)) as target:
            src.backup(target)
        check_integrity(path)
    except BaseException:
        for suffix in ("", "-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)
        raise
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="qAIUIck local SQLite data utility")
    cmd = parser.add_subparsers(dest="command", required=True)
    for command in ("backup", "restore", "export", "import", "check-schema", "integrity"):
        sub = cmd.add_parser(command)
        if command in ("backup", "export", "check-schema", "integrity"):
            sub.add_argument("--db", required=True)
        if command in ("backup", "export", "import", "restore"):
            sub.add_argument("--output", required=True)
        if command in ("restore", "import"):
            sub.add_argument("--source", required=True)
        if command == "check-schema":
            sub.add_argument("--spec", required=True)
        if command == "export":
            sub.add_argument("--app", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("backup", "export", "check-schema", "integrity"):
            if not Path(args.db).is_file():
                raise ValueError("Source SQLite database does not exist")
            store = SQLiteStore(args.db)
        if args.command == "backup":
            path = store.backup(args.output)
            print("QAIUICK_BACKUP_OK", str(path))
        elif args.command == "restore":
            path = restore_new(args.source, args.output)
            print("QAIUICK_RESTORE_NEW_OK", str(path))
            print("Original SQLite database was not modified")
        elif args.command == "export":
            path, digest = export_json(store, args.app, args.output)
            print("QAIUICK_EXPORT_OK", str(path), digest)
        elif args.command == "import":
            path = import_json(args.output, args.source)
            print("QAIUICK_IMPORT_NEW_OK", str(path))
            print("Original SQLite database was not modified")
        elif args.command == "check-schema":
            status, message = check_schema(store, args.spec)
            print("QAIUICK_SCHEMA_" + status, message)
            if status == "BLOCKED":
                return 3
        elif args.command == "integrity":
            check_integrity(args.db)
            print("QAIUICK_INTEGRITY_OK", args.db)
        return 0
    except (StoreError, ValueError, OSError, sqlite3.Error, KeyError, TypeError, json.JSONDecodeError) as error:
        print("QAIUICK_DATA_ERROR", str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
