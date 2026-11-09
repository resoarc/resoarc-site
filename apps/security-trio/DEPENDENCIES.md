# Dependencies and supply-chain status (Security Trio v0.3.0-rc4)

- **Runtime from source**: CPython 3.10+; standard library including bundled `tkinter` / Tcl/Tk. `tkinterdnd2` is optional for drag and drop.
- **GitHub Windows unsigned CI**: CPython 3.12 (major/minor), `pyinstaller==6.22.3`, `tkinterdnd2==0.4.3`. The builder produces three separate one-file EXEs and records a dependency snapshot.
- **Python wrapper**: tkinterdnd2 0.4.3, MIT as listed by PyPI; includes TkDND components.
- **TkDND**: upstream permissive Tcl/Tk-style terms. The 0.4.3 wheel and actually embedded Windows x64 DLL were identified; original source notices are bundled with the new review ZIP. See [THIRD_PARTY.md](THIRD_PARTY.md).
- **PyInstaller**: GPL-2.0-or-later with Bootloader Exception; generated programs can be redistributed subject to the licenses of their dependencies. PyInstaller's own licensing and bootloader exception must be evaluated on the exact version used.
- **Network**: scanning code does not implement uploading user files or HTTP calls. Build-tool installation, GitHub Actions and the public website use networks. No assertion about all possible OS/runtime network activity is made.
- **Unsigned public preview**: v0.3.0-rc4 EXEs were published as an **unsigned development preview** on https://resoarc-security-trio.pages.dev/ and are explicitly labeled as such. Do not disable SmartScreen or Defender to run them.
- **Formal signature status**: no SignPath account approval or code signing certificate is in place. Signed releases must pass independently reviewed dependency, provenance and signature gates.
- **Third-party license notice audit (2026-11-09)**: maintainer review of the identified direct and embedded components is complete; the unsigned CI ZIP contains original licenses/notices with fail-closed checks. This is not a third-party legal opinion, not a complete dependency/SBOM provenance certification, and does not satisfy SignPath eligibility automatically. See [THIRD_PARTY.md](THIRD_PARTY.md).
- **Security/release review**: independent manual security review and the actual signed-release acceptance are still pending.

Useful upstream references:
- https://pypi.org/project/tkinterdnd2/0.4.3/
- https://github.com/petasis/tkdnd/blob/master/license.terms
- https://pyinstaller.org/en/stable/license.html

- **Runtime library inventory**: OpenSSL 3.0.16, zlib 1.3.1, libbzip2, liblzma, libmpdec and Microsoft C runtime are documented in the third-party review and bundled notices.
