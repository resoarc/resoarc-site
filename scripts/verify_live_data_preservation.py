#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Fail closed when a full-site Pages deploy would roll back public SWWW data.

These static snapshots can be updated by a separate publisher. A full-site
Direct Upload must not overwrite a newer or otherwise different live copy.
This pre-deploy check is read-only; it never writes production data.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

SITE = Path(__file__).resolve().parents[1] / "site"
BASE = "https://resoarc.com"
SNAPSHOT_FILES = (
    "/api/v1/swww/catalog.json",
    "/api/v1/swww/advisories.xml",
    "/security/weather/today.json",
)
MAX_BYTES = 8 * 1024 * 1024


def fetch_live(path: str) -> bytes:
    if path not in SNAPSHOT_FILES:
        raise ValueError("unexpected snapshot path")
    request = Request(
        BASE + path,
        headers={"User-Agent": "ResoArc-Public-Snapshot-Guard/1.0",
                 "Accept": "application/octet-stream",
                 "Cache-Control": "no-cache"},
    )
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f"live HTTP {response.status}")
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError("live snapshot exceeds size limit")
        return content


def check(fetch: Callable[[str], bytes] | None = None,
          site: Path = SITE) -> tuple[bool, list[str]]:
    fetcher = fetch if fetch is not None else fetch_live
    errors: list[str] = []
    for path in SNAPSHOT_FILES:
        candidate_path = site / path.lstrip("/")
        if not candidate_path.is_file():
            errors.append(f"missing candidate snapshot: {path}")
            continue
        if candidate_path.stat().st_size > MAX_BYTES:
            errors.append(f"candidate snapshot exceeds size limit: {path}")
            continue
        try:
            live = fetcher(path)
            if len(live) > MAX_BYTES:
                raise ValueError("live snapshot exceeds size limit")
            candidate_sha = hashlib.sha256(candidate_path.read_bytes()).digest()
            live_sha = hashlib.sha256(live).digest()
            if candidate_sha != live_sha:
                errors.append(f"live snapshot differs from candidate: {path}")
        except Exception as exc:
            errors.append(f"cannot verify live snapshot {path}: {exc}")
    return not errors, errors


def main() -> int:
    success, errors = check()
    for error in errors:
        print("BLOCK: " + error, file=sys.stderr)
    if not success:
        return 1
    print(f"PASS: all {len(SNAPSHOT_FILES)} SWWW snapshots match the current live bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
