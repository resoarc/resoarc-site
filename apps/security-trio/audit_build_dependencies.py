"""Inventory actual installed Windows build dependencies and bundled native code.

This is reproducible evidence for *review*, not a complete SBOM or a license
clearance certificate. It must not claim the built executable is signed.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DIST = Path(__file__).resolve().parent
PACKAGES = ("PyInstaller", "tkinterdnd2")
NATIVE_SUFFIXES = {".dll", ".pyd", ".so", ".dylib", ".exe"}
LICENSE_HINTS = ("license", "licence", "notice", "copying", "copyright")


def inspect_distribution(package: str) -> dict:
    distribution = metadata.distribution(package)
    files = distribution.files
    if not files:
        raise RuntimeError(f"BLOCK: installed package file manifest unavailable: {package}")
    native = []
    licenses = []
    for rel in sorted(files, key=lambda p: str(p).lower()):
        rel_name = str(rel).replace("\\", "/")
        local = Path(distribution.locate_file(rel))
        if not local.is_file():
            continue
        if rel.suffix.lower() in NATIVE_SUFFIXES:
            with local.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            native.append({
                "wheel_path": rel_name,
                "size_bytes": local.stat().st_size,
                "sha256": digest,
            })
        if any(k in rel.name.lower() for k in LICENSE_HINTS):
            licenses.append(rel_name)
    return {
        "package": distribution.metadata.get("Name", package),
        "version": distribution.version,
        "declared_license": distribution.metadata.get("License", ""),
        "license_expression": distribution.metadata.get("License-Expression", ""),
        "license_files_present": licenses,
        "native_binaries_in_installed_distribution": native,
    }


def main() -> int:
    entries = [inspect_distribution(package) for package in PACKAGES]
    observed = {r["package"].lower(): r for r in entries}
    expected_versions = {"pyinstaller": "6.22.3", "tkinterdnd2": "0.4.3"}
    for key, expected in expected_versions.items():
        if key not in observed or observed[key]["version"] != expected:
            raise RuntimeError(f"BLOCK: unexpected build dependency version: {key}")
    output = {
        "status": "REVIEW_ONLY_NOT_SIGNED_NOT_A_COMPLETE_SBOM",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "packages": entries,
        "license_review_notes": [
            "Wheel license metadata is not a legal review of embedded native components.",
            "TkDND DLLs are bundled third-party binaries: verify original license.terms and notices before signing.",
            "Include licenses and attribution where required; do not assume the entire EXE is MIT.",
            "Inspect all transitive imports/binaries and a complete SBOM before a general signed release.",
        ],
    }
    destination = DIST / "dist" / "SUPPLY_CHAIN_REVIEW.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("INVENTORY: " + str(destination))
    for item in entries:
        print(f"  {item['package']}=={item['version']}: license files={len(item['license_files_present'])}, native files={len(item['native_binaries_in_installed_distribution'])}")
    print("REVIEW HOLD: bundled licenses and comprehensive SBOM require independent verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
