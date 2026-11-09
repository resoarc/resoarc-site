"""Build a review-only Windows distribution with mandatory third-party notices.

The code-signing input remains EXACTLY three unsigned EXEs. This separate ZIP
is NOT a signed release. Do not deploy or publish it without release approval.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
LICENSES = ROOT / "third_party_licenses"
BINARIES = ("ResoArcSecretScout.exe", "ResoArcLogLantern.exe", "ResoArcFileInspector.exe")
EXPECTED = {
    "CPython-3.12-LICENSE.txt": ("A. HISTORY OF THE SOFTWARE", "Python Software Foundation"),
    "Tcl-license.terms": ("Regents of the University", "copyright"),
    "Tk-license.terms": ("Regents of the University", "copyright"),
    "TkinterDnD2-LICENSE.txt": ("MIT License", "Philippe Gagn"),
    "TkDND-license.terms": ("Georgios Petasis", "permission"),
    "OpenSSL-3-LICENSE.txt": ("Apache License", "Version 2.0"),
    "Zlib-1.3.1-LICENSE.txt": ("Jean-loup Gailly", "Permission is granted"),
    "CPython-Windows-CRT-terms.txt": ("Microsoft Distributable Code", "Windows"),
    "CPython-3.12-incorporated-notices.rst": ("History and License", "libmpdec"),
    "bzip2-1.0.8-LICENSE.txt": ("Julian R Seward", "Redistribution and use"),
    "XZ-Utils-5.4.6-COPYING.txt": ("XZ Utils Licensing", "liblzma"),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pyinstaller_license() -> bytes:
    distribution = importlib.metadata.distribution("pyinstaller")
    if distribution.version != "6.22.3":
        raise ValueError("BLOCK: unexpected PyInstaller build tool version")
    for candidate in distribution.files or ():
        if str(candidate).replace("\\", "/").lower().endswith("/licenses/copying.txt"):
            data = Path(distribution.locate_file(candidate)).read_bytes()
            if b"Bootloader Exception" not in data or len(data) < 1000:
                raise ValueError("BLOCK: missing PyInstaller Bootloader Exception license terms")
            return data
    raise ValueError("BLOCK: PyInstaller license file missing")


def main() -> None:
    if sys.platform != "win32" or sys.version_info[:2] != (3, 12):
        raise ValueError("BLOCK: this audited review package requires Windows Python 3.12")
    if importlib.metadata.version("tkinterdnd2") != "0.4.3":
        raise ValueError("BLOCK: unexpected TkinterDnD2 version")
    src_license = ROOT / "LICENSE"
    if not src_license.is_file() or "MIT License" not in src_license.read_text(encoding="utf-8"):
        raise ValueError("BLOCK: missing ResoArc MIT license")
    checksums = (DIST / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    listed = dict(line.strip().split("  ", 1)[::-1] for line in checksums)
    if len(listed) != 3 or set(listed) != set(BINARIES):
        raise ValueError("BLOCK: executable manifest names mismatch")
    for name in BINARIES:
        if not (DIST / name).is_file() or digest(DIST / name) != listed[name]:
            raise ValueError(f"BLOCK: unsigned EXE hash mismatch: {name}")
    for name, required in EXPECTED.items():
        text = (LICENSES / name).read_text(encoding="utf-8")
        if len(text) < 500 or not all(term.lower() in text.lower() for term in required):
            raise ValueError(f"BLOCK: incomplete license text: {name}")

    notices = """# ResoArc Security Trio: third-party software notices
These notices accompany the **UNSIGNED Windows x64 review candidate**.
The EXEs remain unsigned; this package is not a SignPath-approved release.
ResoArc's own application code is distributed under its MIT license (LICENSE.txt).

| Component | Distribution | License / copied original |
| --- | --- | --- |
| CPython 3.12 runtime and standard library | Embedded | Python Software Foundation License v2 and incorporated-software notices; third_party_licenses/CPython-3.12-LICENSE.txt |
| Tcl 8.6 | Tkinter runtime | Tcl/Tk-style terms; third_party_licenses/Tcl-license.terms |
| Tk 8.6 | GUI runtime | Tcl/Tk-style terms; third_party_licenses/Tk-license.terms |
| TkinterDnD2 0.4.3 (Philippe Gagné) | GUI DnD wrapper | MIT; third_party_licenses/TkinterDnD2-LICENSE.txt |
| TkDND 2.9.4 (Georgios Petasis and contributors) | Native Windows x64 DnD extension | TkDND permissive terms; third_party_licenses/TkDND-license.terms |
| PyInstaller 6.22.3 (build tool/bootloader) | PyInstaller bootloader embedded in EXE | GPL-2.0-or-later with Bootloader Exception; third_party_licenses/PyInstaller-COPYING.txt |
| OpenSSL 3.x (`libcrypto-3.dll`) | CPython hash backend | Apache-2.0; third_party_licenses/OpenSSL-3-LICENSE.txt |
| zlib (`zlib1.dll`) | CPython compression backend | Zlib; third_party_licenses/Zlib-1.3.1-LICENSE.txt (upstream source license from zlib 1.3.1; actual compiled runtime version must be checked) |
| Microsoft Visual C Runtime (`VCRUNTIME140*.dll`, `ucrtbase.dll`, API-set shims) | Python Windows binary system runtime | Microsoft Distributable Code redistribution conditions; third_party_licenses/CPython-Windows-CRT-terms.txt; Windows-only |
| libbzip2 1.0.8 (`_bz2.pyd`) | Embedded CPython extension | bzip2/libbzip2 license; third_party_licenses/bzip2-1.0.8-LICENSE.txt |
| liblzma (XZ Utils, `_lzma.pyd`) | Embedded CPython extension | Original XZ Utils 5.4.6 COPYING documents public-domain liblzma; third_party_licenses/XZ-Utils-5.4.6-COPYING.txt |
| libmpdec (`_decimal.pyd`) and other incorporated CPython code | Embedded CPython extension | CPython incorporated-software notices (BSD-style among others); third_party_licenses/CPython-3.12-incorporated-notices.rst |



Upstream references:
- https://github.com/python/cpython/tree/3.12
- https://github.com/tcltk/tcl/tree/core-8-6-branch
- https://github.com/tcltk/tk/tree/core-8-6-branch
- https://pypi.org/project/tkinterdnd2/0.4.3/
- https://github.com/petasis/tkdnd
- https://pyinstaller.org/en/stable/license.html
- https://openssl-library.org/source/license/index.html
- https://www.zlib.net/zlib_license.html
- https://github.com/python/cpython/blob/3.12/PC/crtlicense.txt
- https://docs.python.org/3.12/license.html
- https://sourceware.org/bzip2/
- https://tukaani.org/xz/

No bundled upstream software is claimed to be authored by ResoArc.
All EXEs are read-only tools, not antivirus or formal security certification.
Review these terms alongside the dependency and native archive inventories.
"""

    package = DIST / "ResoArc-Security-Trio-Windows-x64-UNSIGNED-review.zip"
    license_entries = {f"third_party_licenses/{name}": (LICENSES / name).read_bytes()
                       for name in EXPECTED}
    license_entries["third_party_licenses/PyInstaller-COPYING.txt"] = pyinstaller_license()
    static_entries = {
        "LICENSE.txt": src_license.read_bytes(),
        "THIRD_PARTY_NOTICES.md": notices.encode("utf-8"),
        "SHA256SUMS.txt": (DIST / "SHA256SUMS.txt").read_bytes(),
    }
    zip_entries = {**license_entries, **static_entries}
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for name in BINARIES:
            output.write(DIST / name, name)
        for name in sorted(zip_entries):
            output.writestr(name, zip_entries[name])
    with zipfile.ZipFile(package) as generated:
        expected = set(BINARIES) | set(zip_entries)
        if set(generated.namelist()) != expected or generated.testzip() is not None:
            raise ValueError("BLOCK: distribution ZIP missing files or failed CRC check")
        for name in BINARIES:
            if hashlib.sha256(generated.read(name)).hexdigest() != listed[name]:
                raise ValueError(f"BLOCK: distribution ZIP executable checksum mismatch: {name}")
        for name in license_entries:
            if generated.read(name) != zip_entries[name]:
                raise ValueError(f"BLOCK: license text not retained verbatim: {name}")
    import zlib, ssl
    print(f"RUNTIME_VERSIONS: zlib={zlib.ZLIB_VERSION}, OpenSSL={ssl.OPENSSL_VERSION}")
    print(f"PASS: review-only distribution package contains {len(expected)} exact files")
    print(f"PASS: {len(BINARIES)} EXE hashes and {len(license_entries)} third-party license originals included")
    print(f"REVIEW_PACKAGE: {package.name} bytes={package.stat().st_size}")
    print("STATUS: NOT SIGNED. A human release approval is still required.")


if __name__ == "__main__":
    main()
