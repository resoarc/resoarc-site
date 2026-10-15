#!/usr/bin/env python3
"""Regenerate the SHA-256 manifest for the exact public site tree."""
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
site = root / "site"
files = sorted((p for p in site.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix())
lines = [hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(root).as_posix()
         for p in files]
target = root / "site-manifest.sha256"
target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"Wrote {len(lines)} hashes: {target.name}")
