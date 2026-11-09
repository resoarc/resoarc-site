#!/usr/bin/env python3
"""Reconstruct the complete public ZIP distribution from exact pinned digests.

The 20 historical immutable assets must be hydrated from GitHub Releases first.
Only the 15 non-mirrored ZIPs may be copied from the published site, and ONLY
if every byte matches the checked-in active inventory. Never replace a
mismatched local file, trust a filename, or treat SHA equality as legal approval.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "site/downloads"
CURRENT = ROOT / "docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261109.json"
MIRROR = ROOT / "docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json"
ALLOWED_HOSTS = {"resoarc.com", "www.resoarc.com", "resoarc.pages.dev"}
MAX_BYTES = 8_000_000


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_exact(row: dict) -> None:
    name = row["asset"]
    target = DOWNLOADS / name
    url = "https://resoarc.com/downloads/" + urllib.parse.quote(name)
    last = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "ResoArc-verified-archive-hydration/1.0"}
            )
            with urllib.request.urlopen(request, timeout=35) as response:
                final = urllib.parse.urlsplit(response.geturl())
                if response.status != 200 or final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
                    raise ValueError("Unapproved source, redirect or HTTP response for " + name)
                raw = response.read(row["bytes"] + 1)
            if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
                raise ValueError("Public bytes differ from pinned inventory for " + name)
            fd, tempname = tempfile.mkstemp(prefix=".verified-", suffix=".part", dir=DOWNLOADS)
            try:
                with os.fdopen(fd, "wb") as dest:
                    dest.write(raw)
                os.replace(tempname, target)
            finally:
                if os.path.exists(tempname):
                    os.unlink(tempname)
            return
        except urllib.error.HTTPError as exc:
            if exc.code not in (502, 503, 504):
                raise
            last = exc
        except urllib.error.URLError as exc:
            last = exc
        if attempt < 2:
            time.sleep(1 << attempt)
    raise RuntimeError(f"Cannot hydrate {name} after bounded retries: {type(last).__name__}")


def hydrate() -> None:
    current = json.loads(CURRENT.read_text(encoding="utf-8"))["packages"]
    historical = {
        x["filename"]: x
        for x in json.loads(MIRROR.read_text(encoding="utf-8"))["assets"]
    }
    if len(current) != 35 or len(historical) != 20:
        raise ValueError("Unexpected archive inventory size")
    if len({r["asset"] for r in current}) != 35:
        raise ValueError("Repeated distribution filename")
    count = 0
    for row in current:
        name = row["asset"]
        if (
            not name.endswith(".zip") or "/" in name or "\\" in name
            or name.startswith(".") or ".." in name
            or not 0 < row["bytes"] <= MAX_BYTES
        ):
            raise ValueError("Unsafe archive inventory entry: " + name)
        if name in historical:
            pin = historical[name]
            if row["sha256"] != pin["sha256"] or row["bytes"] != pin["bytes"]:
                raise ValueError("Active inventory disagrees with immutable release: " + name)
        target = DOWNLOADS / name
        if not target.is_file():
            if name in historical:
                raise ValueError("Historical asset missing; hydrate the official GitHub Release first: " + name)
            download_exact(row)
            count += 1
        raw = target.read_bytes()
        if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
            raise ValueError("Local archive has unapproved bytes: " + name)
    print(f"PASS: {len(current)} ZIPs pinned, {len(historical)} from official release mirror; {count} additional exact-hash downloads")
    print("Non-mirrored 15 archives rely on public byte availability until independent archival; legal approval not implied")


if __name__ == "__main__":
    try:
        hydrate()
    except (ValueError, OSError, RuntimeError, KeyError, urllib.error.URLError) as exc:
        print("CURRENT_DISTRIBUTION_HYDRATION_FAIL", str(exc), file=sys.stderr)
        sys.exit(1)
