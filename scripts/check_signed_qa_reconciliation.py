#!/usr/bin/env python3
"""Fail-closed consistency check for the eight signed QA ZIPs and public metadata.

Historical 2026-11-06 inventory is preserved, not silently rewritten.
Cryptographic signature validity and independent rights review are separate.
"""
from __future__ import annotations
import hashlib, io, json, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "site/downloads"
AUDIT = ROOT / "docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json"
ACTIVE = ROOT / "docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261109.json"


def verify() -> None:
    qa = json.loads((DOWNLOADS / "resoarc-signed-qa-manifest.json").read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    inventory = json.loads(ACTIVE.read_text(encoding="utf-8"))
    recognition = json.loads((ROOT / "site/recognition/reuse-signed-archives.json").read_text(encoding="utf-8"))
    catalog = (DOWNLOADS / "index.html").read_text(encoding="utf-8")
    pin = {row["filename"]: row for row in audit["assets"]}
    live_rows = {row["asset"]: row for row in inventory["packages"]}
    provenance = {row["filename"]: row for row in recognition["archives"]}
    assert qa["notice"] == "SIGNED_QA_ONLY_NOT_TENANT_TESTED"
    assert len(qa["plugins"]) == 8
    assert len(live_rows) == 35
    for row in qa["plugins"]:
        name = row["filename"]
        assert name in pin and name in live_rows and name in provenance, name
        expected = pin[name]
        assert row["sha256"] == expected["sha256"] == live_rows[name]["sha256"] == provenance[name]["sha256"], name
        assert row["bytes"] == expected["bytes"] == live_rows[name]["bytes"], name
        assert catalog.count(row["sha256"]) == 1, f"Public catalog SHA missing/duplicated: {name}"
        assert catalog.count('href="/downloads/' + name + '"') == 1, name
        archive = DOWNLOADS / name
        assert archive.is_file(), f"Signed QA archive missing: {name}"
        data = archive.read_bytes()
        assert len(data) == expected["bytes"], name
        assert hashlib.sha256(data).hexdigest() == expected["sha256"], name
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            nested = z.read("contents.zip")
        assert hashlib.sha256(nested).hexdigest() == provenance[name]["payload_sha256"], name
    assert inventory["technical_download_integrity_pass"] is None
    print("PASS: eight signed QA ZIPs match immutable release mirror, public catalog, active license inventory and recognition metadata")
    print("LIMITATION: SHA match is not cryptographic signature validity, tenant acceptance or legal rights approval")


if __name__ == "__main__":
    try:
        verify()
    except (AssertionError, OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        print("SIGNED_QA_RECONCILIATION_FAIL", str(exc), file=sys.stderr)
        sys.exit(1)
