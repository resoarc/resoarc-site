# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""SQLite-backed qAIUIck record storage: transactional, revisioned, fail-closed.

No third-party packages; only Python 3.10+ standard library.
Storage is *record-oriented SQLite* with JSON columns, not arbitrary SQL execution.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

APP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,99}$")
FIELDS = {"type", "required", "min", "max", "step", "minLength",
          "maxLength", "integer", "unique", "options", "default"}
MAX_ROWS = 2000


def stable_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StoreError(Exception):
    status = 400

    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


class Conflict(StoreError):
    status = 409


class InvalidSchema(StoreError):
    status = 422


class SQLiteStore:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.setup()

    def connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def setup(self):
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS apps(
                  app_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                  schema_version INTEGER NOT NULL, fields_json TEXT NOT NULL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS records(
                  app_id TEXT NOT NULL, record_id TEXT NOT NULL,
                  ordinal INTEGER NOT NULL, data_json TEXT NOT NULL,
                  PRIMARY KEY(app_id,record_id),
                  FOREIGN KEY(app_id) REFERENCES apps(app_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS records_order ON records(app_id,ordinal);
            """)

    @staticmethod
    def schema_shape(schema, app_id=None):
        if not isinstance(schema, dict):
            raise InvalidSchema("schema_invalid", "仕様JSONがありません")
        identifier = schema.get("id")
        if not isinstance(identifier, str) or not APP_ID.fullmatch(identifier):
            raise InvalidSchema("id_invalid", "アプリIDが不正です")
        if app_id is not None and identifier != app_id:
            raise InvalidSchema("id_mismatch", "仕様のアプリIDが一致しません")
        version = schema.get("version")
        if type(version) is not int or version < 1:
            raise InvalidSchema("version_invalid", "仕様のバージョンが不正です")
        fields = schema.get("fields")
        if not isinstance(fields, dict) or not 1 <= len(fields) <= 30:
            raise InvalidSchema("fields_invalid", "項目定義が不正です")
        shape = {}
        for name, definition in fields.items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_$][\w$]*", name) or name in ("id", "__proto__", "constructor", "prototype"):
                raise InvalidSchema("field_invalid", "不正な項目名です")
            if not isinstance(definition, dict) or definition.get("type") not in (
                "text", "number", "date", "textarea", "checkbox", "select"):
                raise InvalidSchema("field_invalid", "項目型が不正です")
            shape[name] = {key: definition[key] for key in sorted(FIELDS) if key in definition}
        stable_json(shape)
        return identifier, version, shape

    @staticmethod
    def check_records(rows, shape):
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise StoreError("invalid_rows", f"保存できるレコードは最大{MAX_ROWS}件です")
        ids = set()
        unique = {key: set() for key, f in shape.items() if f.get("unique")}
        for row in rows:
            if not isinstance(row, dict):
                raise StoreError("invalid_record", "レコードはオブジェクトにしてください")
            rid = row.get("id")
            if not isinstance(rid, str) or not 1 <= len(rid) <= 150 or rid in ids:
                raise StoreError("duplicate_id", "レコードIDが不正または重複しています")
            ids.add(rid)
            if set(row) - (set(shape) | {"id"}):
                raise StoreError("unknown_fields", "未定義の項目が含まれています")
            if len(stable_json(row).encode("utf-8")) > 64000:
                raise StoreError("record_too_large", "レコードが64KBを超えています")
            for key, definition in shape.items():
                value = row.get(key)
                if value is None:
                    if definition.get("required"):
                        raise StoreError("required_missing", key + "は必須です")
                    continue
                kind = definition["type"]
                if kind == "checkbox":
                    if type(value) is not bool:
                        raise StoreError("invalid_type", key + "は真偽値が必要です")
                elif kind == "number":
                    if type(value) not in (int, float) or not -1e100 < value < 1e100:
                        raise StoreError("invalid_type", key + "は数値が必要です")
                    if definition.get("integer") and (type(value) is float and not value.is_integer()):
                        raise StoreError("integer_required", key + "は整数で入力してください")
                    if definition.get("min") is not None and value < definition["min"]:
                        raise StoreError("out_of_range", key + "が最小値を下回っています")
                    if definition.get("max") is not None and value > definition["max"]:
                        raise StoreError("out_of_range", key + "が最大値を超えています")
                else:
                    if not isinstance(value, str):
                        raise StoreError("invalid_type", key + "は文字列が必要です")
                    if definition.get("required") and not value.strip():
                        raise StoreError("required_missing", key + "は必須です")
                    if len(value) < definition.get("minLength", 0) and value:
                        raise StoreError("text_too_short", key + "が短すぎます")
                    if definition.get("maxLength") is not None and len(value) > definition["maxLength"]:
                        raise StoreError("text_too_long", key + "が長すぎます")
                    if kind == "select" and value not in definition.get("options", []):
                        raise StoreError("invalid_option", key + "の選択肢が不正です")
                if key in unique and value != "":
                    signature = value.casefold().strip() if isinstance(value, str) else stable_json(value)
                    if signature in unique[key]:
                        raise StoreError("duplicate_unique", key + "が重複しています")
                    unique[key].add(signature)

    @staticmethod
    def validate_schema(existing, schema, app_id):
        _, version, shape = SQLiteStore.schema_shape(schema, app_id)
        current_shape = json.loads(existing["fields_json"])
        if stable_json(shape) != stable_json(current_shape):
            raise Conflict("schema_changed",
                "保存済みデータと項目定義が異なります。バックアップと移行レビューが必要です。")
        if version < existing["schema_version"]:
            raise Conflict("version_rollback", "以前の仕様バージョンから更新できません")
        return version, shape

    @staticmethod
    def load_rows(db, app_id):
        return [
            json.loads(row["data_json"])
            for row in db.execute("SELECT data_json FROM records WHERE app_id=? ORDER BY ordinal", (app_id,))
        ]

    @staticmethod
    def write_rows(db, app_id, rows):
        db.execute("DELETE FROM records WHERE app_id=?", (app_id,))
        db.executemany(
            "INSERT INTO records(app_id,record_id,ordinal,data_json) VALUES(?,?,?,?)",
            [(app_id, row["id"], i, stable_json(row)) for i, row in enumerate(rows)],
        )

    def initialize(self, app_id, schema, sample):
        identifier, version, shape = self.schema_shape(schema, app_id)
        self.check_records(sample, shape)
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT * FROM apps WHERE app_id=?", (identifier,)).fetchone()
                if existing is None:
                    now = utc_now()
                    db.execute(
                        "INSERT INTO apps(app_id,revision,schema_version,fields_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                        (app_id, 0, version, stable_json(shape), now, now))
                    self.write_rows(db, app_id, sample)
                    revision = 0
                else:
                    new_version, _ = self.validate_schema(existing, schema, app_id)
                    if new_version > existing["schema_version"]:
                        db.execute("UPDATE apps SET schema_version=?,updated_at=? WHERE app_id=?",
                                   (new_version, utc_now(), app_id))
                    revision = existing["revision"]
                rows = self.load_rows(db, app_id)
                db.execute("COMMIT")
                return {"items": rows, "revision": revision}
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def update(self, app_id, schema, rows, revision):
        if type(revision) is not int or revision < 0:
            raise StoreError("revision_required", "保存世代が必要です")
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT * FROM apps WHERE app_id=?", (app_id,)).fetchone()
                if not existing:
                    raise Conflict("not_initialized", "アプリが初期化されていません")
                version, shape = self.validate_schema(existing, schema, app_id)
                if existing["revision"] != revision:
                    raise Conflict("stale_revision",
                        "別のタブで変更されています。再読み込みしてから操作してください。")
                self.check_records(rows, shape)
                self.write_rows(db, app_id, rows)
                now = utc_now()
                db.execute("UPDATE apps SET revision=?,schema_version=?,updated_at=? WHERE app_id=?",
                           (revision + 1, version, now, app_id))
                db.execute("COMMIT")
                return {"revision": revision + 1}
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def export_app(self, app_id):
        if not APP_ID.fullmatch(app_id):
            raise InvalidSchema("id_invalid", "アプリIDが不正です")
        with self.connect() as db:
            existing = db.execute("SELECT * FROM apps WHERE app_id=?", (app_id,)).fetchone()
            if not existing:
                raise StoreError("not_found", "アプリが見つかりません")
            return {
                "format": "qaiuick-sqlite-export-v1",
                "id": app_id,
                "version": existing["schema_version"],
                "revision": existing["revision"],
                "fields": json.loads(existing["fields_json"]),
                "items": self.load_rows(db, app_id),
                "exported_at": utc_now(),
            }

    def backup(self, output):
        dest = Path(output).resolve()
        if dest == self.path or dest.exists():
            raise ValueError("Backup target must be a new, distinct file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.connect() as src, sqlite3.connect(str(dest)) as target:
                src.backup(target)
                integrity = target.execute("PRAGMA quick_check").fetchone()[0]
                if integrity != "ok":
                    raise ValueError("Backup integrity check failed: " + integrity)
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        return dest
