#!/usr/bin/env python3
"""Minimal dependency-free reproducible check for the published static tree."""
from __future__ import annotations

import hashlib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REQUIRED = (
    "index.html",
    "404.html",
    "robots.txt",
    "sitemap.xml",
    "llms.txt",
    "assets/tools/hash.js",
    "assets/tools/csv.js",
    "assets/site-20261015-v5.css",
    "assets/resoarc-icon.svg",
    "assets/fonts/noto-serif-jp-v5.woff2",
    "licenses/NOTOSERIFJP-OFL.txt",
    "licenses/RESOARC-MIT.txt",
    "license/index.html",
    "tools/hash/index.html",
    "tools/csv/index.html",
)
SENSITIVE = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*[\"'][A-Za-z0-9_./+=-]{20,}"),
    re.compile(r"C:\\Users\\", re.I),
    # Identity-specific exclusion rules are applied privately before publication.
)

class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []
        self.ids = set()
        self.html_lang = ""
        self.title_present = False
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang", "")
        if tag == "title":
            self._in_title = True
        if "id" in a:
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append(a[key])
    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
    def handle_data(self, data):
        if self._in_title and data.strip():
            self.title_present = True

def to_target(ref):
    url = urlsplit(ref.strip())
    if url.scheme or url.netloc or ref.startswith("//"):
        return None
    raw = unquote(url.path)
    if not raw:
        return None
    target = SITE / raw.lstrip("/")
    if raw.endswith("/") or target.is_dir():
        target /= "index.html"
    return target

def main() -> int:
    errors = []
    def fail(message):
        errors.append(message)

    if not SITE.is_dir():
        print("FAIL: site/ missing")
        return 1

    for path in REQUIRED:
        if not (SITE / path).is_file():
            fail("missing: " + path)
    pages = sorted(SITE.rglob("*.html"))
    files = sorted(p for p in SITE.rglob("*") if p.is_file())
    if not pages:
        fail("no HTML pages")

    for page in pages:
        text = page.read_text(encoding="utf-8")
        relative = page.relative_to(SITE).as_posix()
        parser = ResourceParser()
        try:
            parser.feed(text)
        except Exception as e:
            fail(f"{relative}: HTML parse error {e}")
            continue
        if not text.lower().lstrip().startswith("<!doctype html>"):
            fail(f"{relative}: missing doctype")
        if parser.html_lang != "ja":
            fail(f"{relative}: html lang not ja")
        if not parser.title_present:
            fail(f"{relative}: missing page title")
        for ref in parser.refs:
            if ref.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                continue
            parsed = urlsplit(ref.strip())
            if parsed.scheme or parsed.netloc or ref.startswith("//"):
                continue
            # site links are root-relative; also support document-relative links
            target = to_target(ref) if ref.startswith("/") else to_target(
                "/" + page.relative_to(SITE).parent.as_posix() + "/" + ref
            )
            if target is not None:
                try:
                    target.relative_to(SITE)
                except ValueError:
                    fail(f"{relative}: out-of-tree reference {ref}")
                    continue
                if not target.is_file():
                    fail(f"{relative}: missing local reference {ref}")

    for p in files:
        if p.suffix.lower() not in {".html", ".css", ".js", ".svg", ".txt", ".xml", ".json"}:
            continue
        try:
            value = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail("not valid UTF-8: " + p.relative_to(SITE).as_posix())
            continue
        for regex in SENSITIVE:
            if regex.search(value):
                fail("possible sensitive information: " + p.relative_to(SITE).as_posix()
                     + " pattern=" + regex.pattern[:40])
    if not (ROOT / "LICENSE").is_file():
        fail("missing root MIT license")
    if not (ROOT / "THIRD_PARTY_NOTICES.md").is_file():
        fail("missing third-party notices")
    if not (ROOT / "AI_USAGE.md").is_file():
        fail("missing AI use policy")
    if "Allow: /" not in (SITE / "robots.txt").read_text(encoding="utf-8"):
        fail("robots policy does not explicitly allow crawling")

    manifest_file = ROOT / "site-manifest.sha256"
    if manifest_file.is_file():
        expected = {}
        for row in manifest_file.read_text(encoding="utf-8").splitlines():
            digest, path = row.split("  ", 1)
            expected[path] = digest
        actual = {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files
        }
        if set(expected) != set(actual):
            fail("manifest file set differs from site/; regenerate with update_manifest.py")
        for path in sorted(set(expected).intersection(actual)):
            if expected[path] != actual[path]:
                fail("checksum mismatch: " + path)
    else:
        fail("missing site-manifest.sha256")

    total = sum(p.stat().st_size for p in files)
    print(f"Files: {len(files)} | HTML pages: {len(pages)} | Bytes: {total:,}")
    print("Reference hashes (first 12 hex):")
    for rel in ("index.html", "assets/tools/hash.js", "assets/tools/csv.js"):
        p = SITE / rel
        if p.is_file():
            print("  ", rel, hashlib.sha256(p.read_bytes()).hexdigest()[:12])
    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for item in errors[:50]:
            print(" - " + item)
        return 1
    print("PASS: local references, required files, and baseline public-source checks")
    print("LIMITATION: security audit, copyright audit, and live deployment equivalence are separate checks.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
