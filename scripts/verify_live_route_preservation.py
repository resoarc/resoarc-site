#!/usr/bin/env python3
"""Fail-closed pre-deploy check: do not remove currently published sitemap routes.

Run against the authenticated operator's canonical deployment checkout. This does
not modify site files, and never fetches credentials or unpublished content.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
LIVE_SITEMAP = "https://resoarc.com/sitemap.xml"
MAX_SITEMAP_BYTES = 512 * 1024
MAX_ITEMS = 10000
NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def get_routes(xml_bytes: bytes) -> set[str]:
    if len(xml_bytes) > MAX_SITEMAP_BYTES:
        raise ValueError("sitemap exceeds size limit")
    root = ElementTree.fromstring(xml_bytes)
    if root.tag not in (NAMESPACE + "urlset", "urlset"):
        raise ValueError("expected sitemap urlset")
    routes: set[str] = set()
    for node in root.findall(NAMESPACE + "url") + root.findall("url"):
        loc = node.findtext(NAMESPACE + "loc") or node.findtext("loc")
        if not loc:
            raise ValueError("sitemap contains empty loc")
        parts = urlsplit(loc.strip())
        if parts.scheme != "https" or parts.netloc != "resoarc.com":
            raise ValueError("foreign or non-HTTPS sitemap location")
        if parts.query or parts.fragment:
            raise ValueError("sitemap location has query or fragment")
        route = unquote(parts.path)
        segments = route.split("/")
        if (not route.startswith("/") or not route.endswith("/") or
            any(seg in (".", "..") for seg in segments) or
            "\\" in route or "//" in route):
            raise ValueError("invalid route path")
        if route in routes:
            raise ValueError("duplicate sitemap loc")
        routes.add(route)
        if len(routes) > MAX_ITEMS:
            raise ValueError("sitemap has too many entries")
    if not routes or "/" not in routes:
        raise ValueError("sitemap has no root page")
    return routes


def validate_candidate(live_bytes: bytes, candidate_bytes: bytes, site: Path) -> tuple[set[str], set[str]]:
    live = get_routes(live_bytes)
    candidate = get_routes(candidate_bytes)
    absent = live - candidate
    missing_files = {r for r in live if r in candidate and
                     not (site / r.lstrip("/") / "index.html").is_file()}
    return absent, missing_files


def main() -> int:
    try:
        req = Request(LIVE_SITEMAP, headers={
            "User-Agent": "ResoArc-Deployment-Route-Guard/1.0",
            "Accept": "application/xml",
            "Cache-Control": "no-cache",
        })
        with urlopen(req, timeout=20) as resp:
            if resp.status != 200:
                raise ValueError(f"live sitemap HTTP {resp.status}")
            live = resp.read(MAX_SITEMAP_BYTES + 1)
        candidate = (SITE / "sitemap.xml").read_bytes()
        missing_routes, missing_files = validate_candidate(live, candidate, SITE)
        print(f"Current live routes: {len(get_routes(live))}; candidate: {len(get_routes(candidate))}")
        if missing_routes:
            print(f"BLOCK: {len(missing_routes)} live routes absent from candidate sitemap:")
            for p in sorted(missing_routes):
                print(" - " + p)
        if missing_files:
            print(f"BLOCK: {len(missing_files)} published routes lack candidate HTML:")
            for p in sorted(missing_files):
                print(" - " + p)
        if missing_routes or missing_files:
            return 1
        print("PASS: no currently listed route will be dropped by this candidate")
        return 0
    except Exception as exc:
        print(f"BLOCK: cannot establish route preservation: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
