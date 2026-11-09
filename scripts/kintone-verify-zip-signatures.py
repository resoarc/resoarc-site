#!/usr/bin/env python3
"""Verify every published kintone plugin wrapper listed in the QA evidence.

This uses OpenSSL to confirm RSA/PKCS#1 v1.5 with SHA-1 over the exact
contents.zip bytes. SHA-1 is legacy: signature math is not publisher identity.
No private key, network access or tenant credentials are required.
"""
from __future__ import annotations
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/kintone-progress/evidence/signed-zip-audit-20261017.json"
MEMBERS = {"PUBKEY", "SIGNATURE", "contents.zip"}


def fail(message: str) -> None:
    raise ValueError("Signature evidence mismatch: " + message)


def check_one(entry: dict) -> None:
    rel = entry["filename"]
    # Never follow evidence entries outside the published downloads directory.
    if not rel.startswith("site/downloads/") or "/" in rel.removeprefix("site/downloads/"):
        fail("unsafe archive path")
    path = (REPO / rel).resolve()
    if not path.is_relative_to((REPO / "site/downloads").resolve()):
        fail("path escapes release directory")
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
        fail("outer SHA-256 differs: " + rel)
    with ZipFile(path) as z:
        if set(z.namelist()) != MEMBERS or len(z.namelist()) != 3:
            fail("not a supported signed ZIP wrapper: " + rel)
        pub = z.read("PUBKEY")
        signature = z.read("SIGNATURE")
        payload = z.read("contents.zip")
    calculated_id = "".join(chr(ord("a") + int(nibble, 16))
                            for nibble in hashlib.sha256(pub).hexdigest()[:32])
    if calculated_id[:8] != entry["plugin_id_prefix"]:
        fail("plugin ID prefix does not match: " + rel)
    if entry["signature_algorithm"] != "RSA-PKCS1v1.5-SHA1" or entry["valid_signature"] is not True:
        fail("invalid evidence algorithm or status: " + rel)
    armored = base64.b64encode(pub).decode("ascii")
    pem = "-----BEGIN PUBLIC KEY-----\n" + "\n".join(
        armored[i:i + 64] for i in range(0, len(armored), 64)
    ) + "\n-----END PUBLIC KEY-----\n"
    with tempfile.TemporaryDirectory(prefix="resoarc-zip-verify-") as t:
        folder = Path(t)
        (folder / "public.pem").write_text(pem, encoding="ascii")
        (folder / "contents.zip").write_bytes(payload)
        (folder / "signature.bin").write_bytes(signature)
        result = subprocess.run(
            ["openssl", "dgst", "-sha1", "-verify", str(folder / "public.pem"),
             "-signature", str(folder / "signature.bin"), str(folder / "contents.zip")],
            capture_output=True, text=True, timeout=10, check=False
        )
        if result.returncode != 0 or "Verified OK" not in result.stdout:
            fail("RSA signature failed: " + rel)
    print("SIGNED OK", rel)


def main() -> int:
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    records = data["artifacts"]
    if data["schema_version"] != 1 or len(records) != 11 or data["count"] != 11 or data["verified"] != 11:
        fail("unexpected signed wrapper inventory")
    filenames = [r["filename"] for r in records]
    if len(set(filenames)) != 11:
        fail("duplicate archive evidence")
    for r in records:
        check_one(r)
    print("Verified: 11 signed ZIP wrappers. Algorithm: RSA/PKCS1v1.5 SHA-1 (legacy).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, FileNotFoundError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
