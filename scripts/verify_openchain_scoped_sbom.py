#!/usr/bin/env python3
"""Validate the *provisional* CycloneDX component inventory for two browser tools.

A passing result proves source-file hashes and local asset reference coverage,
not third-party rights, a complete dependency audit, ISO/IEC 5230 compliance
or correspondence between GitHub and the production Cloudflare deployment.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SBOM_PATH = ROOT / "docs/compliance/OPENCHAIN_BROWSER_TOOLS_20261106.cdx.json"
SCOPED_FILES = {
    "site/tools/hash/index.html",
    "site/tools/csv/index.html",
    "site/assets/tools/hash.js",
    "site/assets/tools/csv.js",
    "site/assets/site-20261015-v10.css",
    "site/assets/recognition-20261017.css",
    "site/assets/resoarc-icon.svg",
    "site/assets/tool-icons/hash.svg",
    "site/assets/tool-icons/csv.svg",
    "site/assets/tool-screens/hash.webp",
    "site/assets/tool-screens/csv.webp",
    "site/assets/fonts/noto-serif-jp-v10.woff2",
    "site/assets/hero-architecture.jpg",
    "site/licenses/RESOARC-MIT.txt",
    "site/licenses/NOTOSERIFJP-OFL.txt",
}
THIRD_PARTY = {
    "site/assets/fonts/noto-serif-jp-v10.woff2": "OFL-1.1",
    "site/assets/hero-architecture.jpg": "Unsplash License",
    "site/licenses/NOTOSERIFJP-OFL.txt": "OFL-1.1",
}


def fail(message: str) -> None:
    raise ValueError(message)


def check() -> None:
    bom = json.loads(SBOM_PATH.read_text(encoding="utf-8"))
    if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        fail("Unexpected CycloneDX format/specVersion")
    components = bom.get("components", [])
    names = [c.get("name") for c in components]
    if len(names) != len(set(names)) or set(names) != SCOPED_FILES:
        fail(f"Missing/extra/duplicate component files: {set(names) ^ SCOPED_FILES}")
    for component in components:
        name = component["name"]
        path = ROOT / name
        if not path.is_file():
            fail("Missing scoped file: " + name)
        if component.get("type") != "file" or component.get("bom-ref") != "file:" + name:
            fail("Invalid file component identity: " + name)
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes = component.get("hashes", [])
        if hashes != [{"alg": "SHA-256", "content": expected}]:
            fail("Source file hash differs: " + name)
        lic = component.get("licenses", [])
        if len(lic) != 1 or "license" not in lic[0]:
            fail("Missing file license annotation: " + name)
        annotation = lic[0]["license"]
        observed = annotation.get("id", annotation.get("name", ""))
        if observed != THIRD_PARTY.get(name, "MIT"):
            fail("Unexpected license annotation: " + name)
    compositions = bom.get("compositions", [])
    if not compositions or compositions[0].get("aggregate") != "incomplete":
        fail("Preliminary inventory must NOT claim completeness")

    # Any new direct local asset referenced by the two pages or linked
    # stylesheets must force a refreshed inventory. Navigation routes are
    # excluded, but actual static assets (including OG previews) are covered.
    asset_refs: set[str] = set()
    for name in ("site/tools/hash/index.html", "site/tools/csv/index.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for raw in re.findall(r'(?:src|href|content)\\s*=\\s*["\\']([^"\\']+)["\\']', text):
            url_path = urlsplit(raw).path
            if url_path.startswith("/assets/"):
                asset_refs.add("site" + url_path)
    for name in ("site/assets/site-20261015-v10.css", "site/assets/recognition-20261017.css"):
        css = (ROOT / name).read_text(encoding="utf-8")
        for raw in re.findall(r'url\\(\\s*["\\']?([^)"\\']+)', css):
            url_path = urlsplit(raw.strip()).path
            if url_path.startswith("/assets/"):
                asset_refs.add("site" + url_path)
    missing_refs = asset_refs - SCOPED_FILES
    if missing_refs:
        fail("Untracked direct asset reference(s): " + ", ".join(sorted(missing_refs)))

    print(f"PASS: {len(SCOPED_FILES)} files and {len(asset_refs)} directly referenced local assets hash-matched")
    print("STATUS: PROVISIONAL / NOT CONFORMANT; third-party licenses, running release process and production delivery unverified")


if __name__ == "__main__":
    try:
        check()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print("FAIL: OpenChain scoped SBOM evidence: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
