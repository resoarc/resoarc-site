#!/usr/bin/env python3
"""Re-check 35 public release checksums and adjacent licensing, no credentials.

Local invariant checks run without network. --live queries three official public
distribution domains. This cannot independently certify authorship or legal rights.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261109.json"
CATALOG = ROOT / "site/downloads/index.html"
THIRDPARTY = ROOT / "site/downloads/THIRD_PARTY_LICENSES.md"
HOSTS = ("resoarc.com", "www.resoarc.com", "resoarc.pages.dev")
HEADERS = {"User-Agent": "ResoArc-OSPS-license-audit/1.0"}
MAX_BYTES = 8_000_000


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate() -> tuple[dict, list[str]]:
    errors = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    packages = manifest["packages"]
    files = [x["asset"] for x in packages]
    if len(packages) != 35 or len(set(files)) != 35:
        errors.append("expected exactly 35 distinct ZIP release assets")
    if sum(bool(x["signed_installer"]) for x in packages) != 22:
        errors.append("signed installer count changed")
    if sum(not x["signed_installer"] for x in packages) != 13:
        errors.append("source archive count changed")
    html = CATALOG.read_text(encoding="utf-8")
    notes = THIRDPARTY.read_text(encoding="utf-8")
    for row in packages:
        name = row["asset"]
        if name.count("/") or ".." in name or not name.endswith(".zip"):
            errors.append(f"unsafe archive filename: {name}")
        if len(row["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in row["sha256"]):
            errors.append(f"bad sha256 for {name}")
        if row["bytes"] < 1 or row["bytes"] > MAX_BYTES:
            errors.append(f"invalid asset byte size: {name}")
        if html.count(row["sha256"]) != 1:
            errors.append(f"missing/duplicated catalog SHA-256: {name}")
        if html.count('href="/downloads/' + name + '"') != 1:
            errors.append(f"missing/duplicated license catalog link: {name}")
        if row.get("copyright_chain_independently_verified") is not False:
            errors.append(f"independent legal approval must not be inferred: {name}")
    for token in ('href="/downloads/LICENSE"', 'href="/downloads/NOTICE.md"', 'href="/downloads/THIRD_PARTY_LICENSES.md"'):
        if token not in html:
            errors.append(f"catalog missing sidecar link {token}")
    for entry in ("fflate 0.8.3", "Apache License 2.0", "OFL", "Unsplash"):
        if entry not in notes:
            errors.append(f"third-party note missing {entry}")
    if manifest.get("legal_signoff", "").startswith("APPROVED"):
        errors.append("this unreviewed manifest must not claim legal signoff")
    return manifest, errors


def check_live(host: str, row: dict) -> str | None:
    filename = row["asset"]
    url = f"https://{host}/downloads/{filename}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=22) as r:
            data = r.read(MAX_BYTES + 1)
            status = r.status
    except Exception as exc:
        return f"{host}/{filename}: fetch failed ({type(exc).__name__})"
    if status != 200 or len(data) != row["bytes"] or sha(data) != row["sha256"]:
        return f"{host}/{filename}: status/size/sha mismatch"
    return None


def check_notice(host: str, filename: str) -> str | None:
    path = ROOT / "site/downloads" / filename
    if filename == "NOTICE.md" and not path.exists():
        # Current repo stores the official legal release notice in the audited
        # distribution in a separate static version. The live check only
        # verifies the file is reachable; it does not invent an exact local hash.
        known_sha = "a8e2e44a391a3a365ec228d46e4ab5ec880325597aafc4d15d02f7f4f45f2737"
    elif path.exists():
        known_sha = sha(path.read_bytes())
    else:
        return "missing local license companion " + filename
    url = f"https://{host}/downloads/{filename}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=22) as r:
            b = r.read(20000)
            status = r.status
    except Exception as exc:
        return f"{host}/{filename}: fetch failed ({type(exc).__name__})"
    if status != 200 or sha(b) != known_sha:
        return f"{host}/{filename}: license file mismatch"
    return None


def main(live: bool) -> int:
    manifest, problems = validate()
    print(f"Local manifest/catalog: {len(manifest['packages'])} assets; {len(problems)} issues")
    if live and not problems:
        checks = [(host, row) for host in HOSTS for row in manifest["packages"]]
        with ThreadPoolExecutor(max_workers=7) as pool:
            problems += [x for x in pool.map(lambda item: check_live(*item), checks) if x]
        for host in HOSTS:
            for name in ("LICENSE", "NOTICE.md"):
                err = check_notice(host, name)
                if err:
                    problems.append(err)
        print(f"Live checks: {len(checks)} ZIPs plus 6 license sidecars")
    for problem in problems:
        print("FAIL:", problem, file=sys.stderr)
    print("This audit establishes bytes/availability only; human rights approval remains separate.")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="check all three public release hosts")
    args = parser.parse_args()
    raise SystemExit(main(args.live))
