#!/usr/bin/env python3
"""Verify the pinned, immutable ResoArcOS PC source archive."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile
import sys

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "site/downloads/resoarcos-pc-v0.1.0-dev-source.zip"
EXPECTED = "72b427a8ef08ab388dc70ad2f1b14bcb2a7517b8f5edd0ebe67c8d934a93bb20"
REQUIRED = {"LICENSE", "scripts/verify-iso.sh", "images/pc/build.sh", "src/resoarcos/firstboot.py", "tests/test_firstboot.py"}

def check():
    if not ARCHIVE.is_file():
        raise ValueError("Missing immutable source archive")
    digest = sha256(ARCHIVE.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise ValueError(f"Pinned source digest mismatch: {digest}")
    with ZipFile(ARCHIVE) as z:
        infos = z.infolist()
        if len(infos) > 500 or sum(i.file_size for i in infos) > 10_000_000:
            raise ValueError("Archive size or count bound exceeded")
        names = set()
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or info.filename.startswith("\\"):
                raise ValueError("Unsafe ZIP pathname")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("Symlink entry forbidden")
            if info.filename in names:
                raise ValueError("Duplicate ZIP entry")
            names.add(info.filename)
        if not REQUIRED.issubset(names):
            raise ValueError(f"Missing required source files: {sorted(REQUIRED - names)}")
    return digest, len(infos)

if __name__ == "__main__":
    try:
        digest, count = check()
        print(f"PASS ResoArcOS source: {count} entries, SHA-256 {digest}")
    except (ValueError, OSError, BadZipFile) as exc:
        print(f"FAIL ResoArcOS source: {exc}", file=sys.stderr)
        sys.exit(1)
