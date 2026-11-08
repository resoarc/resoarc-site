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
import time
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "site/downloads"
AUDIT = ROOT / "docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json"
TAG = "resoarc-osps-distribution-mirror-20261106"
REPO = "resoarc/resoarc-site"
HEADERS = {"User-Agent": "ResoArc-OSPS-artifact-check", "Accept": "application/vnd.github+json"}
MAX_BYTES = 16_000_000

# Retry only transient transport/5xx failures. Never retry digest mismatches,
# malformed metadata, or non-transient authorization/not-found responses.
def _urlopen_with_bounded_retry(request, timeout: float):
    for attempt in range(3):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in (502, 503, 504) or attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise
        time.sleep(1 << attempt)
    raise AssertionError("retry loop exhausted")



def fetch_json(url: str) -> dict:
    with _urlopen_with_bounded_retry(urllib.request.Request(url, headers=HEADERS), timeout=40) as response:
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
            with _urlopen_with_bounded_retry(urllib.request.Request(url, headers=HEADERS), timeout=80) as response:
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



def check_public_download_without_api(row: dict, hydrate: bool) -> None:
    """Byte-verify the canonical public Release URL when unauthenticated API is throttled.

    Never trust a redirect target, Content-Length, or an asset filename alone.
    Download all bytes and compare with repository-pinned SHA-256 and size.
    """
    name = row["filename"]
    url = f"https://github.com/{REPO}/releases/download/{TAG}/{urllib.parse.quote(name)}"
    target = DOWNLOADS / name
    if target.is_file() and (
        target.stat().st_size != row["bytes"] or hash_file(target) != row["sha256"]
    ):
        raise ValueError(f"Local asset has invalid pinned digest: {name}")

    should_save = hydrate and not target.is_file()
    tempname = None
    fd = None
    if should_save:
        fd, tempname = tempfile.mkstemp(prefix=".osps-direct-", suffix=".part", dir=DOWNLOADS)
    count = 0
    digest = hashlib.sha256()
    try:
        with _urlopen_with_bounded_retry(
            urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]}),
            timeout=80,
        ) as response:
            if response.status != 200:
                raise ValueError(f"Direct release download returned {response.status}: {name}")
            with (os.fdopen(fd, "wb") if should_save else open(os.devnull, "wb")) as dest:
                fd = None
                for piece in iter(lambda: response.read(131072), b""):
                    count += len(piece)
                    if count > MAX_BYTES or count > row["bytes"]:
                        raise ValueError(f"Direct release exceeds pinned size: {name}")
                    digest.update(piece)
                    if should_save:
                        dest.write(piece)
        if count != row["bytes"] or digest.hexdigest() != row["sha256"]:
            raise ValueError(f"Direct release bytes differ from immutable audit: {name}")
        if should_save:
            os.replace(tempname, target)
            tempname = None
    finally:
        if fd is not None:
            os.close(fd)
        if tempname is not None and os.path.exists(tempname):
            os.unlink(tempname)


def check_direct_release(expected: list[dict], hydrate: bool) -> None:
    for row in expected:
        check_public_download_without_api(row, hydrate)
    for name in ("LICENSE", "NOTICE.md"):
        local = DOWNLOADS / name
        if not local.is_file():
            raise ValueError(f"Missing required license companion: {name}")
        check_public_download_without_api(
            {"filename": name, "bytes": local.stat().st_size, "sha256": hash_file(local)},
            False,
        )


def main(hydrate: bool) -> None:
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    expected = data["assets"]
    if len(expected) != 20 or len({row["filename"] for row in expected}) != 20:
        raise ValueError("Historical distribution inventory has changed unexpectedly")
    try:
        assets = mirror_map()
    except urllib.error.HTTPError as exc:
        limited = exc.code == 403 and (
            exc.headers.get("X-RateLimit-Remaining") == "0"
            or b"rate limit" in exc.read(500).lower()
        )
        # The release API occasionally returns a transient 502/503/504. After
        # bounded retries, use the same fail-closed, byte-verified public URL
        # path already used when unauthenticated API quota is exhausted.
        # Any missing, changed, truncated or unauthenticated data still fails.
        fallback = limited or exc.code in (502, 503, 504)
        if not fallback:
            raise
        check_direct_release(expected, hydrate)
        print(
            f"INFO: GitHub API HTTP {exc.code}; "
            "verified direct Release downloads using repository-pinned SHA-256"
        )
    else:
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
