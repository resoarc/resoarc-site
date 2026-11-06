#!/usr/bin/env python3
"""Verify release user-guide coverage against all known software assets."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/RELEASED_PRODUCT_GUIDES.md"
AUDIT = ROOT / "docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json"

def check() -> list[str]:
    text = GUIDE.read_text(encoding="utf-8")
    inventory = json.loads(AUDIT.read_text(encoding="utf-8"))["assets"]
    issues = []
    if len(inventory) != 20:
        issues.append("asset inventory no longer has exactly 20 archived ZIP records")
    for row in inventory:
        if text.count(row["filename"]) != 1:
            issues.append("release guide reference missing or duplicated: " + row["filename"])
    pages = sorted((ROOT / "site/tools").glob("*/index.html"))
    for page in pages:
        relative = page.relative_to(ROOT).as_posix()
        if relative not in text:
            issues.append("tool user guide not linked: " + relative)
        html = page.read_text(encoding="utf-8")
        if not re.search(r"<h1(?:\s[^>]*)?>", html):
            issues.append("product page missing H1: " + relative)
    for path in (ROOT / "site/products/kintone/qa/index.html",
                 ROOT / "site/products/web/index.html",
                 ROOT / "site/os/index.html"):
        if path.relative_to(ROOT).as_posix() not in text:
            issues.append("missing release collection link: " + path.as_posix())
    return issues

if __name__ == "__main__":
    problems = check()
    for problem in problems:
        print("FAIL:", problem, file=sys.stderr)
    print("Product guide coverage:", 20, "historical archives and", len(list((ROOT / "site/tools").glob("*/index.html"))), "user pages")
    raise SystemExit(1 if problems else 0)
