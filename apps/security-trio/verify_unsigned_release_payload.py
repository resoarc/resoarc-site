"""Fail-closed validation of CI-produced Security Trio UNSIGNED release package.

Works on a GitHub Ubuntu release runner without starting or extracting any EXE.
Requires the successful Windows CI run as additional Authenticode/PE evidence.
No GitHub API, signing credentials, network, destructive writes, or dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

RELEASE_ZIP = "ResoArc-Security-Trio-Windows-x64-UNSIGNED-review.zip"
EXECUTABLES = (
    "ResoArcSecretScout.exe",
    "ResoArcLogLantern.exe",
    "ResoArcFileInspector.exe",
)
NOTICES = (
    "CPython-3.12-LICENSE.txt",
    "CPython-3.12-incorporated-notices.rst",
    "CPython-Windows-CRT-terms.txt",
    "OpenSSL-3-LICENSE.txt",
    "PyInstaller-COPYING.txt",
    "Tcl-license.terms",
    "Tk-license.terms",
    "TkDND-license.terms",
    "TkinterDnD2-LICENSE.txt",
    "XZ-Utils-5.4.6-COPYING.txt",
    "Zlib-1.3.1-LICENSE.txt",
    "bzip2-1.0.8-LICENSE.txt",
)
FILES = set(EXECUTABLES) | {"LICENSE.txt", "SHA256SUMS.txt", "THIRD_PARTY_NOTICES.md"} | {
    "third_party_licenses/" + name for name in NOTICES
}
MAX_BUNDLE_BYTES = 100 * 1024 * 1024


class ReleaseValidationError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _members(z: zipfile.ZipFile, *, expected: set[str], scope: str) -> dict[str, zipfile.ZipInfo]:
    members = z.infolist()
    names = [entry.filename for entry in members]
    if len(names) != len(expected) or set(names) != expected:
        raise ReleaseValidationError(f"{scope}: exact entry set mismatch, duplicate or missing entries")
    if any(entry.is_dir() or entry.flag_bits & 0x1 or entry.file_size > MAX_BUNDLE_BYTES
           for entry in members):
        raise ReleaseValidationError(f"{scope}: directories, encryption or oversize rejected")
    if sum(entry.file_size for entry in members) > MAX_BUNDLE_BYTES:
        raise ReleaseValidationError(f"{scope}: excessive uncompressed size")
    if z.testzip() is not None:
        raise ReleaseValidationError(f"{scope}: CRC check failed")
    return {entry.filename: entry for entry in members}


def parse_manifest(data: bytes) -> dict[str, str]:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ReleaseValidationError("manifest must use ASCII") from exc
    found: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (ResoArc(?:SecretScout|LogLantern|FileInspector)\.exe)", line)
        if not match or match.group(2) in found:
            raise ReleaseValidationError("invalid or duplicate manifest entry")
        found[match.group(2)] = match.group(1)
    if set(found) != set(EXECUTABLES):
        raise ReleaseValidationError("manifest EXE count mismatch")
    return found


def verify_artifact_folder(root: Path) -> dict:
    """Check bytes in exactly one CI output folder, no executable invocation."""
    dist = root / "dist"
    if dist.is_symlink() or not dist.is_dir():
        raise ReleaseValidationError("missing dist directory")
    outer_file = dist / RELEASE_ZIP
    if outer_file.is_symlink() or not outer_file.is_file() or outer_file.stat().st_size > MAX_BUNDLE_BYTES:
        raise ReleaseValidationError("invalid bundled ZIP file")
    actual = {entry.name for entry in dist.iterdir()}
    expected_dist = set(EXECUTABLES) | {
        "SHA256SUMS.txt", "SUPPLY_CHAIN_REVIEW.json", "FROZEN_CONTENTS_REVIEW.json",
        "LICENSE_COVERAGE_REVIEW.json", RELEASE_ZIP
    }
    if actual != expected_dist:
        raise ReleaseValidationError("dist output files differ from pinned CI manifest")
    if any(p.is_symlink() or not p.is_file() for p in dist.iterdir()):
        raise ReleaseValidationError("symlink/non-file input rejected")
    manifest_bytes = (dist / "SHA256SUMS.txt").read_bytes()
    manifest = parse_manifest(manifest_bytes)
    with zipfile.ZipFile(outer_file) as z:
        _members(z, expected=FILES, scope="release bundle")
        if z.read("SHA256SUMS.txt") != manifest_bytes:
            raise ReleaseValidationError("inner manifest differs from CI manifest")
        for filename, digest in manifest.items():
            inner = z.read(filename)
            if sha256(inner) != digest:
                raise ReleaseValidationError(f"inner binary hash failed: {filename}")
            if sha256((dist / filename).read_bytes()) != digest:
                raise ReleaseValidationError(f"outer binary hash failed: {filename}")
        if b"MIT License" not in z.read("LICENSE.txt"):
            raise ReleaseValidationError("own project license missing")
        notices = z.read("THIRD_PARTY_NOTICES.md")
        if b"UNSIGNED" not in notices or b"not a SignPath-approved release" not in notices:
            raise ReleaseValidationError("required unsigned license disclosure missing")
        for name in NOTICES:
            content = z.read("third_party_licenses/" + name)
            if len(content) < 500:
                raise ReleaseValidationError("license original incomplete")
    coverage = json.loads((dist / "LICENSE_COVERAGE_REVIEW.json").read_text(encoding="utf-8"))
    if coverage.get("status") != "PASS_LICENSE_NOTICE_COVERAGE_NOT_LEGAL_CERTIFICATION":
        raise ReleaseValidationError("release component license gate incomplete")
    if coverage.get("native_components_per_executable") != 61:
        raise ReleaseValidationError("unexpected native component count")
    if coverage.get("third_party_notice_files") != len(NOTICES):
        raise ReleaseValidationError("notice count unexpected")
    if set(coverage.get("covered_notice_files", [])) != set(NOTICES):
        raise ReleaseValidationError("license coverage mismatch")
    return {
        "status": "PASS",
        "kind": "UNSIGNED_WINDOWS_X64_SOURCE_CI_ARTIFACT_VERIFICATION",
        "signed": False,
        "human_external_review": False,
        "signpath_approved": False,
        "release_authorized_by": "ResoArc internal AI review policy",
        "binary_sha256": manifest,
        "release_zip_sha256": sha256(outer_file.read_bytes()),
        "license_originals": len(NOTICES),
        "native_component_count_per_executable": 61,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_artifact_folder(args.artifact_root)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print("BLOCK: release artifact validation failed: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
