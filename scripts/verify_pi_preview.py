#!/usr/bin/env python3
"""Verify the published Raspberry Pi source-only snapshot without a local OS checkout."""
from __future__ import annotations
import hashlib
import sys
import zipfile
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
NAME="resoarcos-pi-firstboot-v0.2.1-alpha-source.zip"
EXPECTED="d8beeccf39f457b45fa469285af6b905b4d4dc11aa8dae36af7b1ac145dd47c1"
REQUIRED={"LICENSE","README.md","images/pi/build.sh","images/pi/resoarc-firstboot.yaml","images/pi/getty-firstboot.sh","src/resoarcos/firstboot.py","tests/test_firstboot.py"}

def main():
    filename=ROOT/"site/downloads"/NAME
    digest=hashlib.sha256(filename.read_bytes()).hexdigest()
    if digest!=EXPECTED:raise ValueError("Pi source digest mismatch: "+digest)
    checksum=(ROOT/"site/downloads"/(NAME+".sha256")).read_text(encoding="ascii")
    if checksum!=f"{EXPECTED}  {NAME}\n":raise ValueError("Checksum file does not match")
    with zipfile.ZipFile(filename) as z:
        info=z.infolist()
        names=set(i.filename for i in info if not i.is_dir())
        if not REQUIRED.issubset(names):raise ValueError("Missing required Pi source entries")
        if len(info)>400 or sum(i.file_size for i in info)>3_000_000:
            raise ValueError("Unreasonably large archive")
        seen=set()
        for i in info:
            path=PurePosixPath(i.filename)
            if i.filename in seen or path.is_absolute() or ".." in path.parts or i.filename.startswith("\\"):
                raise ValueError("Unsafe Pi source path")
            seen.add(i.filename)
            if (i.external_attr>>16)&0o170000==0o120000:
                raise ValueError("Symlink forbidden in Pi source")
        if b"def validate_public_key" not in z.read("src/resoarcos/firstboot.py"):
            raise ValueError("First-boot public key checks absent")
        if b"test_console_reprompts_invalid_wifi_key_and_mode_without_writes" not in z.read("tests/test_firstboot.py"):
            raise ValueError("First-boot regression test absent")
    html=(ROOT/"site/os/pi/index.html").read_text(encoding="utf8")
    if NAME not in html or "実機未検証" not in html or EXPECTED not in html:
        raise ValueError("Pi landing page missing warning or archive link")
    print("PASS PI_PREVIEW_SOURCE",len(names),"files",digest)

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,zipfile.BadZipFile) as e:
        print("FAIL PI_PREVIEW_SOURCE:",e,file=sys.stderr);sys.exit(1)
