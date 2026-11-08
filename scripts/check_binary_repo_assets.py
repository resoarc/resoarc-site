#!/usr/bin/env python3
"""Reject generated executable / unreviewable binary blobs in source control."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs/compliance/BINARY_ASSET_REVIEW_20261106.json"
RECOVERED_INVENTORY = ROOT / "docs/compliance/PRODUCTION_ASSET_RECOVERY_20261108.json"
FORBIDDEN = {".zip", ".exe", ".dll", ".iso", ".jar", ".class", ".wasm",
             ".o", ".a", ".so", ".dylib", ".app", ".bin", ".rom", ".pyc"}
MAGICS = {
    "png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
    "jpeg": lambda b: b.startswith(b"\xff\xd8"),
    "woff2": lambda b: b.startswith(b"wOF2"),
    "ico": lambda b: b.startswith(b"\x00\x00\x01\x00"),
}

def audit() -> list[str]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    recovered = json.loads(RECOVERED_INVENTORY.read_text(encoding="utf-8"))
    if len(inventory["assets"]) != 34 or len(recovered["assets"]) != 31:
        return ["reviewed asset inventory count changed without source review"]
    expected = {x["path"]: x for x in [*inventory["assets"], *recovered["assets"]]}
    if len(expected) != 65:
        return ["duplicate binary asset inventory path"]
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    errors = []
    for name in tracked:
        path = ROOT / name
        if not path.is_file():
            errors.append(f"missing source file {name}")
            continue
        if path.suffix.lower() in FORBIDDEN:
            errors.append(f"generated executable/blob in git source: {name}")
        data = path.read_bytes()
        if data.startswith(b"\x7fELF") or data[:2] == b"MZ":
            errors.append(f"executable binary magic detected: {name}")
        if name in expected:
            item = expected[name]
            if item["format"] not in MAGICS or not MAGICS[item["format"]](data):
                errors.append(f"asset header/format mismatch: {name}")
            if item["size"] != len(data) or item["sha256"] != hashlib.sha256(data).hexdigest():
                errors.append(f"asset integrity changed without review: {name}")
            license_id = ("OFL-1.1" if item["format"] == "woff2" else
                          "LicenseRef-Unsplash" if name.endswith(("hero-architecture.jpg", "hero-architecture-1600.webp", "hero-architecture-800.webp")) else
                          "LicenseRef-ThirdPartyMarks" if name.startswith("site/assets/recognition/") else "MIT")
            if item["license_expression"] != license_id:
                errors.append(f"asset license metadata mismatch: {name}")
        elif b"\x00" in data[:4096]:
            errors.append(f"new unreviewed binary/nontext source: {name}")
    extra = set(expected) - set(tracked)
    if extra:
        errors.append("reviewed asset inventory no longer matches tracked tree: " + str(sorted(extra)))
    if len(expected) != 65:
        errors.append(f"expected reviewed graphic/font assets: 65, now {len(expected)}")
    return errors


if __name__ == "__main__":
    errors = audit()
    for issue in errors:
        print("FAIL:", issue, file=sys.stderr)
    print(f"Current source-tree binary audit: 65 visual/font assets, {len(errors)} issues")
    print("The archive release and historical git commits are not overwritten or claimed to be independent audits.")
    raise SystemExit(1 if errors else 0)
