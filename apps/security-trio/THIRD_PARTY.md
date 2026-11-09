# Third-party license review | ResoArc Security Trio

Review date: **2026-11-09 (JST)**. Scope: **three Windows x64 PyInstaller one-file EXEs** in the *unsigned* Security Trio CI review candidate, built from public source on GitHub Actions with CPython 3.12, PyInstaller 6.22.3 and TkinterDnD2 0.4.3.

## Result and scope

**Third-party license identification, original notice collection and release-ZIP retention checks: completed for the components identified below.** This is a maintainer's license compliance review, **not an opinion of a qualified lawyer, a source-to-binary attestation of every upstream project, an independent security audit, or SignPath approval**.

The CI now blocks a review package unless all required source license/notice files are present, basic provenance markers are intact, the three EXEs match `SHA256SUMS.txt`, and all 12 third-party notice texts are reproduced verbatim inside the unsigned review ZIP. The GitHub signing workflow also performs this notice preflight before submitting its **separate three-EXE-only** signing artifact. Actual signed-release packaging is not enabled.

## Contents and license obligations

| Component | Actual role/version | License and redistribution action |
| --- | --- | --- |
| ResoArc Security Trio app source | Our three Python applications | MIT; `LICENSE` included in review ZIP |
| CPython interpreter/stdlib | 3.12.x, embedded in each EXE | PSF License v2; `CPython-3.12-LICENSE.txt` and the upstream `CPython-3.12-incorporated-notices.rst` both bundled |
| Tcl / Tk | Tcl/Tk 8.6 embedded with `_tkinter.pyd` | TCL/TK License (`TCL` SPDX); full Tcl and Tk `license.terms` texts bundled, notices preserved |
| TkinterDnD2 | 0.4.3, shipped DnD wrapper | MIT; `TkinterDnD2-LICENSE.txt` bundled; **the 0.4.3 PyPI Wheel LICENSE SHA-256 matches the upstream source LICENSE SHA-256** |
| TkDND | 2.9.4, `libtkdnd2.9.4.dll` + Tcl files for win-x64 | Upstream TkDND/Tcl-style license; Georgios Petasis and related copyright notices retained verbatim in `TkDND-license.terms` |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later with **Bootloader Exception**; permission to distribute generated combined EXEs under MIT. Complete installed `COPYING.txt` copied into the ZIP for transparency even though upstream says this is not mandatory for generated EXEs |
| OpenSSL | 3.0.16, `libcrypto-3.dll` used by CPython `_hashlib.pyd` | Apache-2.0; complete OpenSSL-3 `LICENSE.txt` bundled |
| zlib | 1.3.1, `zlib1.dll` | zlib License; upstream 1.3.1 license header bundled |
| libbzip2 | 1.0.8, CPython `_bz2.pyd` | bzip2/libbzip2 permissive license; upstream 1.0.8 `LICENSE` bundled |
| liblzma | CPython `_lzma.pyd` | Older XZ Utils liblzma is public domain; XZ Utils 5.4.6 `COPYING` included as evidence. This is for the core library, not unrelated command-line scripts |
| libmpdec and other CPython-incorporated software | CPython `_decimal.pyd`, `unicodedata.pyd`, etc. | Corresponding third-party copyright and redistribution notices supplied by CPython's version-specific `Doc/license.rst` (including libmpdec's BSD-style binary notice) |
| Microsoft Visual C / Universal CRT | `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`, `ucrtbase.dll` and Windows API-set DLLs | Proprietary **Microsoft Distributable Code**, not MIT/OSS. Python's Windows `PC/crtlicense.txt` is included. Windows-only redistribution; preserve copyright/trademark notices, do not imply Microsoft endorsement, and do not use the code on other platforms. Relevant Microsoft redistribution terms and end-user protection requirements remain applicable |

**Important:** Build-environment-only Python dependencies (`altgraph`, `pefile`, `pyinstaller-hooks-contrib`, etc.) are not separately redistributed as their complete installed packages in the EXE. Runtime hooks and embedded copies, where present, must retain their applicable upstream notices as part of PyInstaller/CPython; the frozen-archive inventory is used to monitor new native libraries in future builds.

## Evidence and release gates

- The actual installed PyInstaller/TkinterDnD2 files, versions, native components and license paths are recorded in `dist/SUPPLY_CHAIN_REVIEW.json`.
- `dist/FROZEN_CONTENTS_REVIEW.json` lists PyInstaller CArchive names for each executable; Windows builds refuse non-win-x64 TkDND DLLs. `audit_frozen_archives.py` also enumerates the native `.dll` and `.pyd` files.
- Windows CI performs a strict `package_unsigned_review.py` step and stores `ResoArc-Security-Trio-Windows-x64-UNSIGNED-review.zip`. The ZIP contains exactly three unsigned EXEs, their SHA-256 manifest, our MIT license, `THIRD_PARTY_NOTICES.md` and 12 original upstream license/notice files. Each ZIP entry is checked and the EXEs are hashed again after packaging.
- This means users of the **review ZIP** receive the required copyright and license information with the downloaded binaries. Older stand-alone `v0.3.0-rc4` preview EXE links on the separate website are **not** automatically updated by GitHub CI.
- The review bundle remains **unsigned and not a production release**. A signed release must be repackaged with hashes of **signed** binaries, the same notices, and an explicit approval record.

## Remaining distinction: SignPath eligibility

The source and native dependencies have permissive redistribution terms, so **copyright notice compliance is not the same thing as signing-program eligibility**. SignPath Foundation's free program calls for OSI-approved licensing for components, but the SPDX `TCL` (Tcl/Tk) license is listed without OSI approval. The Microsoft C runtime is proprietary System Library code. Whether these are accepted under SignPath's program terms must be **explicitly decided by SignPath**. The security-scanner eligibility inquiry is already sent; no acceptance has been received.

No legal statement here promises that SignPath Foundation will sign the project. Pending approval, continue publishing only **clearly labeled unsigned development builds**.

## Upstream documents

- [CPython 3.12 license](https://docs.python.org/3.12/license.html)
- [Tcl/Tk license identifier](https://spdx.org/licenses/TCL.html)
- [TkinterDnD2](https://pypi.org/project/tkinterdnd2/0.4.3/)
- [TkDND source license](https://github.com/petasis/tkdnd/blob/master/license.terms)
- [PyInstaller Bootloader Exception](https://pyinstaller.org/en/stable/license.html)
- [OpenSSL 3 licensing](https://openssl-library.org/source/license/index.html)
- [zlib](https://www.zlib.net/zlib_license.html)
- [bzip2 1.0.8](https://sourceware.org/bzip2/)
- [XZ Utils](https://tukaani.org/xz/)
- [Python Windows CRT conditions](https://github.com/python/cpython/blob/3.12/PC/crtlicense.txt)
- [SignPath OSS conditions](https://signpath.org/terms.html)
