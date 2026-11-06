#!/usr/bin/env python3
"""Verify/hydrate the immutable GitHub Release mirror for historical ZIP assets.

The audit JSON pins exact names, sizes, and SHA-256. Source and distribution
checks must NEVER accept an unverified replacement, silently re-sign a package,
or infer license conformance just because hashes match.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "site/downloads"
AUDIT = ROOT / "docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json"
TAG = "resoarc-osps-distribution-mirror-20261106"
REPO = "resoarc/resoarc-site"
HEADERS = {"User-Agent": "ResoArc-OSPS-artifact-check", "Accept": "application/vnd.github+json"}
MAX_BYTES = 16_000_000


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as response:
        return json.load(response)


def load_release() -> dict:
    return fetch_json(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(131072), b""):
            h.update(chunk)
    return h.hexdigest()


def mirror_map() -> dict:
    release = load_release()
    if release.get("draft"):
        raise ValueError("Mirror release is a draft")
    return {a["name"]: a for a in release.get("assets", [])}


def check_remote(assets: dict, expected: list[dict]) -> None:
    expected_names = {row["filename"] for row in expected} | {"LICENSE", "NOTICE.md"}
    missing = expected_names - set(assets)
    if missing:
        raise ValueError(f"Release mirror missing required assets: {sorted(missing)}")
    for row in expected:
        asset = assets[row["filename"]]
        if asset.get("state") != "uploaded" or asset.get("size") != row["bytes"]:
            raise ValueError(f"Release size/state mismatch: {row['filename']}")
        digest = asset.get("digest")
        if digest and digest.lower() != "sha256:" + row["sha256"]:
            raise ValueError(f"Release digest mismatch: {row['filename']}")
    for name in ("LICENSE", "NOTICE.md"):
        asset = assets[name]
        path = DOWNLOADS / name
        digest = asset.get("digest")
        if not path.is_file() or asset.get("size") != path.stat().st_size:
            raise ValueError(f"Missing/mismatched notice sidecar: {name}")
        if digest and digest.lower() != "sha256:" + hash_file(path):
            raise ValueError(f"License/notice digest mismatch: {name}")


def fetch_asset(row: dict, url: str) -> None:
    target = DOWNLOADS / row["filename"]
    if target.is_file():
        if target.stat().st_size != row["bytes"] or hash_file(target) != row["sha256"]:
            raise ValueError(f"Existing file fails pinned SHA-256: {row['filename']}")
        return
    fd, tempname = tempfile.mkstemp(prefix=".osps-asset-", suffix=".part", dir=DOWNLOADS)
    try:
        h = hashlib.sha256()
        total = 0
        with os.fdopen(fd, "wb") as dest:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=80) as response:
                while True:
                    chunk = response.read(131072)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_BYTES or total > row["bytes"]:
                        raise ValueError(f"Release exceeds pinned size: {row['filename']}")
                    h.update(chunk)
                    dest.write(chunk)
        if total != row["bytes"] or h.hexdigest() != row["sha256"]:
            raise ValueError(f"Downloaded asset differs from immutable audit: {row['filename']}")
        os.replace(tempname, target)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)


def main(hydrate: bool) -> None:
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    expected = data["assets"]
    if len(expected) != 20 or len({row["filename"] for row in expected}) != 20:
        raise ValueError("Historical distribution inventory has changed unexpectedly")
    assets = mirror_map()
    check_remote(assets, expected)
    if hydrate:
        for row in expected:
            fetch_asset(row, assets[row["filename"]]["browser_download_url"])
    print(f"PASS: {len(expected)} historical ZIP release assets and LICENSE/NOTICE verified")
    print("No product security, license-delivery or OpenChain conformance assertion is implied.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hydrate", action="store_true", help="download only missing ZIPs to site/downloads after exact SHA-256 verification")
    args = parser.parse_args()
    try:
        main(args.hydrate)
    except (ValueError, OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: GitHub release mirror check: {exc}", file=sys.stderr)
        raise SystemExit(1)
