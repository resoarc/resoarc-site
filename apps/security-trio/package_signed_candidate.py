"""Build a review-only ZIP from SignPath-verified signed Security Trio EXEs.

This command NEVER signs binaries and NEVER publishes a release. A failed
Authenticode, signed hash, provenance or license check prevents packaging.
The resulting ZIP is a signed-CANDIDATE artifact requiring human approval.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from package_unsigned_review import EXPECTED, ROOT, DIST, LICENSES, BINARIES, digest, pyinstaller_license

SIGNED = ROOT / "signed"
PACKAGED = DIST / "ResoArc-Security-Trio-Windows-x64-SIGNED-candidate-not-released.zip"
SOURCE_LICENSE = ROOT / "LICENSE"
CERT_RE = re.compile(r"^[0-9A-Fa-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
EXACT_NAMES = set(BINARIES) | {"SHA256SUMS.txt"}


def checked_signed_inputs(directory: Path) -> dict[str, str]:
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("BLOCK: signed output directory missing or redirected")
    children = list(directory.iterdir())
    if {p.name for p in children} != EXACT_NAMES:
        raise ValueError("BLOCK: signed output contains missing or unexpected files")
    if any(not p.is_file() or p.is_symlink() for p in children):
        raise ValueError("BLOCK: signed output contains link or non-file")
    lines = (directory / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    expected: dict[str, str] = {}
    for line in lines:
        m = re.fullmatch(r"([0-9a-f]{64})  (ResoArc[A-Za-z]+\.exe)", line)
        if m is None or m.group(2) in expected:
            raise ValueError("BLOCK: malformed or duplicate signed SHA256SUMS entry")
        expected[m.group(2)] = m.group(1)
    if set(expected) != set(BINARIES):
        raise ValueError("BLOCK: signed hash manifest must contain exactly three EXEs")
    for name, claimed in expected.items():
        if digest(directory / name) != claimed:
            raise ValueError(f"BLOCK: signed EXE SHA-256 mismatch: {name}")
    return expected


def signing_evidence() -> dict:
    thumb = os.getenv("EXPECTED_SIGNER_THUMBPRINT", "").strip()
    request_id = os.getenv("SIGNPATH_SIGNING_REQUEST_ID", "").strip()
    request_url = os.getenv("SIGNPATH_SIGNING_REQUEST_URL", "").strip()
    sha = os.getenv("GITHUB_SHA", "").strip()
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if not CERT_RE.fullmatch(thumb):
        raise ValueError("BLOCK: approved signing certificate fingerprint absent")
    if not request_id or len(request_id) > 150:
        raise ValueError("BLOCK: actual SignPath signing request ID required")
    parsed = urlsplit(request_url)
    if (parsed.scheme != "https" or not parsed.hostname or
            not (parsed.hostname == "signpath.io" or parsed.hostname.endswith(".signpath.io")) or
            parsed.username is not None or parsed.password is not None):
        raise ValueError("BLOCK: trusted SignPath signing request URL required")
    if not CERT_RE.fullmatch(sha) or not run_id.isdecimal():
        raise ValueError("BLOCK: verified GitHub source commit and workflow run required")
    return {
        "status": "SIGNED_CANDIDATE_NOT_PUBLISHED",
        "source_commit_sha": sha,
        "github_workflow_run_id": run_id,
        "signpath_signing_request_id": request_id,
        "signpath_signing_request_url": request_url,
        "approved_signer_sha1_thumbprint": thumb.upper(),
        "expected_publisher": "SignPath Foundation",
        "human_release_approval": "PENDING",
        "signing_workflow_verification": "Windows Authenticode validated before and during packaging",
    }


def enforce_authenticode(thumbprint: str) -> None:
    if sys.platform != "win32":
        raise RuntimeError("BLOCK: Windows Authenticode verification required")
    command = [
        "pwsh", "-NoProfile", "-NonInteractive", "-File",
        str(ROOT / "verify_signed_release.ps1"),
        "-Dist", str(SIGNED),
        "-ExpectedPublisher", "SignPath Foundation",
        "-ExpectedCertificateThumbprint", thumbprint,
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("BLOCK: signed release verification failed; do not distribute") from exc


def package() -> None:
    evidence = signing_evidence()
    # Revalidate signatures independently of the preceding workflow step.
    # This check is read-only and must never regenerate or overwrite a manifest.
    enforce_authenticode(evidence["approved_signer_sha1_thumbprint"])
    signed_hashes = checked_signed_inputs(SIGNED)
    if "MIT License" not in SOURCE_LICENSE.read_text(encoding="utf-8"):
        raise ValueError("BLOCK: project MIT license missing")
    original_licenses = {
        "third_party_licenses/" + name: (LICENSES / name).read_bytes()
        for name in EXPECTED
    }
    for name, requirements in EXPECTED.items():
        text = original_licenses["third_party_licenses/" + name].decode("utf-8")
        if len(text) < 500 or not all(marker.lower() in text.lower() for marker in requirements):
            raise ValueError(f"BLOCK: third-party license missing or modified: {name}")
    original_licenses["third_party_licenses/PyInstaller-COPYING.txt"] = pyinstaller_license()
    notice = (
        "# ResoArc Security Trio: notices for signed candidate\n\n"
        "The three EXEs in this package passed Windows Authenticode signature\n"
        "validation against the release policy and a pinned certificate fingerprint.\n"
        "This is a **release candidate, not an approved or published release**.\n"
        "An authorized maintainer must review and approve the complete package.\n\n"
        "The ResoArc application code is MIT-licensed (LICENSE.txt). The complete\n"
        "third-party license originals are provided under third_party_licenses/.\n"
        "Third-party components include CPython, Tcl/Tk, TkinterDnD2, TkDND,\n"
        "OpenSSL, zlib, bzip2, liblzma, libmpdec, PyInstaller and Windows CRT.\n"
        "No rights to third-party code are claimed by ResoArc.\n"
        "The authoritative hashes of the **signed** EXEs are SHA256SUMS.txt.\n"
    )
    entries = {
        **original_licenses,
        "LICENSE.txt": SOURCE_LICENSE.read_bytes(),
        "THIRD_PARTY_NOTICES.md": notice.encode("utf-8"),
        "SHA256SUMS.txt": (SIGNED / "SHA256SUMS.txt").read_bytes(),
        "SIGNING_EVIDENCE.json": (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    }
    DIST.mkdir(exist_ok=True)
    if PACKAGED.exists():
        raise ValueError("BLOCK: refusing to overwrite an existing signed candidate")
    with zipfile.ZipFile(PACKAGED, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in BINARIES:
            z.write(SIGNED / name, name)
        for name in sorted(entries):
            z.writestr(name, entries[name])
    with zipfile.ZipFile(PACKAGED, "r") as z:
        if z.testzip() is not None or set(z.namelist()) != set(BINARIES) | set(entries):
            raise ValueError("BLOCK: invalid signed release candidate contents")
        for name in BINARIES:
            if hashlib.sha256(z.read(name)).hexdigest() != signed_hashes[name]:
                raise ValueError("BLOCK: post-packaging signed hash mismatch")
        for name, data in entries.items():
            if z.read(name) != data:
                raise ValueError(f"BLOCK: post-packaging notice/evidence mismatch: {name}")
    print(f"PASS: signed candidate packaging verified ({len(entries) + len(BINARIES)} files)")
    print("PASS: signed SHA-256, pinned certificate, SignPath request provenance and license texts")
    print(f"CANDIDATE_ONLY: {PACKAGED.name}")


if __name__ == "__main__":
    package()
