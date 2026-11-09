#!/usr/bin/env python3
"""Fail closed when a full-site deploy would roll back independently published SWWW snapshots.

Live snapshot inputs can be changed by a separate scheduled publishing workflow.
Full-site Pages Direct Upload must not silently replace them with older files.
"""
from __future__ import annotations
import hashlib
import sys
from pathlib import Path
from urllib.request import Request, urlopen

SITE = Path(__file__).resolve().parents[1] / "site"
BASE = "https://resoarc.com"
SNAPSHOT_FILES = (
    "/api/v1/swww/catalog.json",
    "/api/v1/swww/advisories.xml",
    "/security/weather/today.json",
)
MAX_BYTES = 8 * 1024 * 1024

def unchanged(candidate: bytes, current: bytes) -> bool:
    return hashlib.sha256(candidate).digest() == hashlib.sha256(current).digest()

def check(fetch=None) -> tuple[bool, list[str]]:
    if fetch is None:
        def fetch(path: str) -> bytes:
            req = Request(BASE + path, headers={
                "User-Agent": "ResoArc-Public-Snapshot-Guard/1.0",
                "Cache-Control": "no-cache",
            })
            with urlopen(req, timeout=20) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}: {path}")
                content = response.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise ValueError(f"snapshot too large: {path}")
                return content

    errors: list[str] = []
    for path in SNAPSHOT_FILES:
        target = SITE / path.lstrip("/")
        if not target.is_file():
            errors.append(f"missing candidate snapshot: {path}")
            continue
        try:
            live = fetch(path)
            if len(live) > MAX_BYTES:
                raise ValueError("oversized live snapshot")
            if not unchanged(target.read_bytes(), live):
                errors.append(f"live snapshot differs from candidate: {path}")
        except Exception as exc:
            errors.append(f"cannot verify live snapshot {path}: {exc}")
    return not errors, errors

def main() -> int:
    good, problems = check()
    for problem in problems:
        print("BLOCK: " + problem, file=sys.stderr)
    if not good:
        return 1
    print(f"PASS: all {len(SNAPSHOT_FILES)} independently updated live SWWW files match candidate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
