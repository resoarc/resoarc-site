#!/usr/bin/env python3
"""Verify immutable release ZIP inventory and license-evidence coverage.

This test checks bytes, archive entries, and the presence of interim sidecars.
It does NOT assert that a license is compatible, users received a notice, or
that ResoArc has passed OSPS Baseline/OpenChain. This distinction is deliberate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "site" / "downloads"
EVIDENCE = ROOT / "docs" / "compliance" / "OSPS_RELEASE_LICENSE_AUDIT_20261106.json"


def run(strict: bool = False) -> int:
    problems: list[str] = []
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    recorded = evidence["assets"]
    expected = {row["filename"] for row in recorded}
    existing = {path.name for path in DOWNLOADS.glob("*.zip")}
    if existing != expected:
        problems.append(f"release ZIP inventory differs: added={sorted(existing - expected)}, missing={sorted(expected - existing)}")

    license_file = DOWNLOADS / "LICENSE"
    root_license = ROOT / "LICENSE"
    if not license_file.is_file() or license_file.read_bytes() != root_license.read_bytes():
        problems.append("site/downloads/LICENSE does not exactly match root MIT LICENSE")
    notice_file = DOWNLOADS / "NOTICE.md"
    if not notice_file.is_file() or "THIRD_PARTY_NOTICES.md" not in notice_file.read_text(encoding="utf-8"):
        problems.append("site/downloads/NOTICE.md or third-party reference missing")

    without_embedded_license = []
    for row in recorded:
        path = DOWNLOADS / row["filename"]
        if not path.is_file():
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != row["sha256"] or len(data) != row["bytes"]:
            problems.append(f"changed distribution bytes without updated license/source audit: {row['filename']}")
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    problems.append(f"corrupt ZIP member in {row['filename']}: {bad}")
                filenames = archive.namelist()
                license_paths = sorted(
                    name for name in filenames
                    if name.rsplit("/", 1)[-1].lower() in {"license", "license.md", "license.txt", "copying", "copying.txt"}
                )
                signed = any(name.rsplit("/", 1)[-1].upper() == "SIGNATURE" for name in filenames)
                if license_paths != row["embedded_license_paths"] or signed != row["signed_installable"]:
                    problems.append(f"archive license/signature inventory changed: {row['filename']}")
                if not license_paths:
                    without_embedded_license.append(row["filename"])
        except (OSError, zipfile.BadZipFile) as exc:
            problems.append(f"unreadable ZIP {row['filename']}: {exc}")

    print(f"OSPS release-license audit: {len(recorded)} tracked ZIP assets")
    print(f"  without embedded LICENSE: {len(without_embedded_license)}")
    print("  companion LICENSE/NOTICE are interim and do not prove delivery to users or license compliance")
    for name in without_embedded_license:
        print(f"  NEEDS DELIVERY VALIDATION: {name}")

    if strict and (without_embedded_license or not evidence.get("distribution_evidence_verified") or not evidence.get("all_license_obligations_verified")):
        problems.append("conformance gate remains HOLD: distribution evidence/full obligations not proven")
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    print("PASS: archived ZIP bytes, entry inventory and interim companion evidence unchanged; NOT A CONFORMANCE RESULT")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail until licensing delivery and all obligations are evidenced")
    args = parser.parse_args()
    raise SystemExit(run(args.strict))
