"""Fail-closed coverage of native components by redistributable license notices.

This is a self-audit for the UNSIGNED Windows x64 CI review artifact. It
must NOT be represented as legal certification, a full SBOM, or SignPath
Foundation's acceptance of any non-OSI/system-library components.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
BINS = ("ResoArcSecretScout.exe", "ResoArcLogLantern.exe", "ResoArcFileInspector.exe")
BUNDLE = "ResoArc-Security-Trio-Windows-x64-UNSIGNED-review.zip"

CPY = "CPython-3.12-LICENSE.txt"
INCORP = "CPython-3.12-incorporated-notices.rst"
CRT = "CPython-Windows-CRT-terms.txt"
PYINSTALLER = "PyInstaller-COPYING.txt"
TKDND = "TkDND-license.terms"
DND2 = "TkinterDnD2-LICENSE.txt"
OPENSSL = "OpenSSL-3-LICENSE.txt"
ZLIB = "Zlib-1.3.1-LICENSE.txt"
BZ2 = "bzip2-1.0.8-LICENSE.txt"
LZMA = "XZ-Utils-5.4.6-COPYING.txt"
TCL = "Tcl-license.terms"
TK = "Tk-license.terms"

ALL_NOTICES = frozenset((
    CPY, INCORP, CRT, PYINSTALLER, TKDND, DND2,
    OPENSSL, ZLIB, BZ2, LZMA, TCL, TK
))

CORE_PYDS = frozenset((
    "_queue.pyd", "_socket.pyd", "_wmi.pyd", "select.pyd", "unicodedata.pyd"
))


def required_notices_for_native(name: str) -> frozenset[str]:
    """Each path must be a recognized installed runtime, or refuse release."""
    n = name.replace("\\", "/").lower()
    if n.startswith("tkinterdnd2/tkdnd/win-x64/libtkdnd") and n.endswith(".dll"):
        return frozenset((TKDND, DND2))
    if "/" in n:
        raise ValueError(f"BLOCK: unreviewed native binary path {name!r}")
    if n in CORE_PYDS or n == "python312.dll":
        return frozenset((CPY, INCORP))
    if n == "_bz2.pyd":
        return frozenset((CPY, INCORP, BZ2))
    if n == "_lzma.pyd":
        return frozenset((CPY, INCORP, LZMA))
    if n == "_decimal.pyd":
        return frozenset((CPY, INCORP))
    if n == "_hashlib.pyd":
        return frozenset((CPY, INCORP, OPENSSL))
    if n == "_tkinter.pyd":
        return frozenset((CPY, INCORP, TCL, TK))
    if n in ("tcl86t.dll", "tk86t.dll"):
        return frozenset((TCL, TK))
    if n == "libcrypto-3.dll":
        return frozenset((OPENSSL,))
    if n == "zlib1.dll":
        return frozenset((ZLIB,))
    if n in ("vcruntime140.dll", "vcruntime140_1.dll", "ucrtbase.dll"):
        return frozenset((CRT,))
    if re.fullmatch(r"api-ms-win-(?:core|crt)-[a-z0-9-]+\.dll", n):
        return frozenset((CRT,))
    raise ValueError(f"BLOCK: unknown native library requires license review: {name}")


def verify_coverage(inventory: dict, archive_names: set[str]) -> dict:
    apps = inventory.get("applications")
    if not isinstance(apps, list) or len(apps) != 3:
        raise ValueError("BLOCK: expected three frozen binaries in inventory")
    if {a.get("binary") for a in apps} != set(BINS):
        raise ValueError("BLOCK: frozen binary names mismatch")

    expected_runtime = None
    covered = set((PYINSTALLER,))
    for app in apps:
        paths = app.get("native_runtime_members")
        if not isinstance(paths, list) or len(paths) != len(set(paths)) or not paths:
            raise ValueError("BLOCK: missing/duplicated native binary inventory")
        if app.get("foreign_platform_tkdnd_members"):
            raise ValueError("BLOCK: cross-platform TkDND payload found")
        current = set(paths)
        if expected_runtime is None:
            expected_runtime = current
        elif current != expected_runtime:
            raise ValueError("BLOCK: inconsistent native components across EXEs")
        for path in paths:
            covered.update(required_notices_for_native(path))
    if covered != set(ALL_NOTICES):
        raise ValueError(f"BLOCK: license coverage set changed: {sorted(set(ALL_NOTICES) - covered)}")
    archived = {name.removeprefix("third_party_licenses/") for name in archive_names
                if name.startswith("third_party_licenses/")}
    if archived != ALL_NOTICES:
        raise ValueError(
            "BLOCK: missing, unexpected or outdated license files: " +
            repr(sorted(ALL_NOTICES.symmetric_difference(archived)))
        )
    for required in ("THIRD_PARTY_NOTICES.md", "SHA256SUMS.txt", "LICENSE.txt", *BINS):
        if required not in archive_names:
            raise ValueError(f"BLOCK: distribution ZIP missing {required}")
    if len(archive_names) != len(BINS) + 3 + len(ALL_NOTICES):
        raise ValueError("BLOCK: unexpected entries in review ZIP")
    return {
        "status": "PASS_LICENSE_NOTICE_COVERAGE_NOT_LEGAL_CERTIFICATION",
        "native_components_per_executable": len(expected_runtime or ()),
        "third_party_notice_files": len(ALL_NOTICES),
        "recognized_native_entries": sorted(expected_runtime or ()),
        "covered_notice_files": sorted(covered),
    }


def main() -> None:
    if sys.platform != "win32":
        raise ValueError("BLOCK: Windows-only native inventory gate")
    inventory = json.loads((DIST / "FROZEN_CONTENTS_REVIEW.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(DIST / BUNDLE) as package:
        names = set(package.namelist())
        result = verify_coverage(inventory, names)
        for license_name in ALL_NOTICES:
            original = HERE / "third_party_licenses" / license_name
            if license_name == PYINSTALLER:
                # The build step imports this license from the pinned wheel.
                import importlib.metadata
                installed = importlib.metadata.distribution("pyinstaller")
                files = [f for f in installed.files or ()
                         if str(f).replace("\\", "/").lower().endswith("/licenses/copying.txt")]
                if len(files) != 1:
                    raise ValueError("BLOCK: unexpected PyInstaller license location")
                original = Path(installed.locate_file(files[0]))
            if package.read("third_party_licenses/" + license_name) != original.read_bytes():
                raise ValueError(f"BLOCK: modified third-party notice {license_name}")
    (DIST / "LICENSE_COVERAGE_REVIEW.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: exact native library allowlist and upstream license notice coverage")
    print("NATIVE_COVERAGE: " + str(result["native_components_per_executable"]))
    print("LICENSE_NOTICES: " + str(result["third_party_notice_files"]))


if __name__ == "__main__":
    main()
