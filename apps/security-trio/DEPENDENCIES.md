# Dependencies and supply-chain status (Security Trio v0.3.0-rc4)

- **Runtime from source**: CPython 3.10+; standard library including bundled `tkinter` / Tcl/Tk. `tkinterdnd2` is optional for drag and drop.
- **GitHub Windows unsigned CI**: CPython 3.12 (major/minor), `pyinstaller==6.22.3`, `tkinterdnd2==0.4.3`. The builder produces three separate one-file EXEs and records a dependency snapshot.
- **Python wrapper**: tkinterdnd2 0.4.3, MIT as listed by PyPI; includes TkDND components.
- **TkDND**: upstream permissive terms with required preserved notices; actual wheels and bundled license texts still require release-level inspection. See [THIRD_PARTY.md](THIRD_PARTY.md).
- **PyInstaller**: GPL-2.0-or-later with Bootloader Exception; generated programs can be redistributed subject to the licenses of their dependencies. PyInstaller's own licensing and bootloader exception must be evaluated on the exact version used.
- **Network**: scanning code does not implement uploading user files or HTTP calls. Build-tool installation, GitHub Actions and the public website use networks. No assertion about all possible OS/runtime network activity is made.
- **Unsigned public preview**: v0.3.0-rc4 EXEs were published as an **unsigned development preview** on https://resoarc-security-trio.pages.dev/ and are explicitly labeled as such. Do not disable SmartScreen or Defender to run them.
- **Formal signature status**: no SignPath account approval or code signing certificate is in place. Signed releases must pass independently reviewed dependency, provenance and signature gates.
- **Security/third-party review**: comprehensive independent testing and complete SBOM of bundled executable dependencies have not been completed.

Useful upstream references:
- https://pypi.org/project/tkinterdnd2/0.4.3/
- https://github.com/petasis/tkdnd/blob/master/license.terms
- https://pyinstaller.org/en/stable/license.html
