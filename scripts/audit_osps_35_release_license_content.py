#!/usr/bin/env python3
"""Live, byte-pinned software-license content check for ResoArc's 35 releases.

Public HTTP inputs only. Requires no credentials; never re-signs or overwrites a
package. No claim of complete infringement, originality, or authorship testing.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json"
LIMIT = 8_000_000
HEADER = {"User-Agent": "ResoArc-OSPS-license-content-audit/1.0"}
CONTENT_SUFFIXES = (".js", ".mjs", ".ts", ".css", ".html", ".py", ".json",
                    ".md", ".txt", ".toml", ".yaml", ".yml", ".sh", ".cjs")
PROHIBITIONS = ("proprietary license", "noncommercial", "non-commercial use only",
                "not for redistribution", "no redistribution", "you may not redistribute",
                "commercial use prohibited")


def unzip(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as stream:
        rows = stream.infolist()
        if len(rows) > 1500 or sum(x.file_size for x in rows) > 70_000_000:
            raise ValueError("unusually large or potentially unsafe archive")
        return {
            x.filename: stream.read(x)
            for x in rows if not x.is_dir() and x.file_size <= 4_000_000
        }


def scan(row: dict) -> dict:
    name = row["asset"]
    url = "https://resoarc.com/downloads/" + name
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADER), timeout=25) as stream:
        content = stream.read(LIMIT + 1)
        status = stream.status
    if status != 200 or len(content) != row["bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
        raise ValueError("release bytes not pinned: " + name)
    archive = unzip(content)
    signed = "contents.zip" in archive and "SIGNATURE" in archive
    files = unzip(archive["contents.zip"]) if signed else archive
    if signed != bool(row["signed_installer"]):
        raise ValueError("signed/source kind changed: " + name)
    texts = {}
    full_mit = False
    for filename, body in files.items():
        if filename.endswith(CONTENT_SUFFIXES) and len(body) <= 2_000_000:
            texts[filename] = body.decode("utf-8", "replace")
        if Path(filename).name.lower() in ("license", "license.md", "license.txt"):
            t = body.decode("utf-8", "replace")
            full_mit |= ("MIT License" in t and
                         "Permission is hereby granted, free of charge" in t and
                         "THE SOFTWARE IS PROVIDED" in t)
    if not signed and not full_mit:
        raise ValueError("full MIT license absent from source archive: " + name)
    flags = []
    for path, source in texts.items():
        lower = source.lower()
        for phrase in PROHIBITIONS:
            if phrase in lower:
                flags.append({"file": path, "phrase": phrase})
    if "qr-code" in name:
        qr = texts.get("js/qr-lib.js", "")
        if not all(t in qr for t in (
            "Copyright (c) 2009 Kazuhiko Arase",
            "MIT License", "Apache License", "Permission is hereby granted",
            "TERMS AND CONDITIONS"
        )):
            raise ValueError("QR copyright or dual license text missing: " + name)
    if "backup-migration" in name:
        mit = [t for k, t in texts.items()
               if "fflate" in k.lower() and "license" in k.lower()]
        if not any("MIT License" in t and "Arjun Barrett" in t for t in mit):
            raise ValueError("fflate upstream license missing: " + name)
    # OFL is free, and the "all rights reserved" part is a copyright notice,
    # not a proprietary prohibition on distribution under OFL.
    return {"asset": name, "signed": signed, "text_members": len(texts),
            "full_mit_inside": full_mit, "restrictive_phrase_flags": flags}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="write observed audit details as JSON")
    opts = parser.parse_args()
    pins = json.loads(MANIFEST.read_text(encoding="utf-8"))["packages"]
    if len(pins) != 35 or len({x["asset"] for x in pins}) != 35:
        raise ValueError("35-release manifest incomplete")
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(scan, pins))
    flagged = [(x["asset"], f) for x in results for f in x["restrictive_phrase_flags"]]
    record = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "35 SHA-256 pinned public releases, nested signed payloads",
              "text_members": sum(x["text_members"] for x in results),
              "source_mit_full_text": sum(x["full_mit_inside"] for x in results),
              "signed_archive_count": sum(x["signed"] for x in results),
              "restrictive_flags": flagged,
              "results": results,
              "claim_boundary": "Mechanical signs only; uncredited copying and copyright ownership cannot be disproven by a scanner."}
    if opts.output:
        opts.output.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print("RELEASES",len(results),"SIGNED",record["signed_archive_count"],
          "TEXT",record["text_members"],"SOURCE_WITH_FULL_MIT",record["source_mit_full_text"],
          "RESTRICTIVE_FLAGS",len(flagged))
    for name, item in flagged:
        print("REVIEW:",name,item["file"],item["phrase"])
    print("No legal certification of authorship or AI model training provenance is made.")
    return 1 if flagged else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("AUDIT FAILED:", type(exc).__name__, str(exc), file=sys.stderr)
        raise SystemExit(2)
