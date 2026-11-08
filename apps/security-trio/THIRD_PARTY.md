# Third-party software inventory and licensing review

This file describes *components expected in the future GitHub-hosted Windows build*. It is **not** an independently verified complete SBOM of the already published unsigned rc4 executables.

| Component | Role | Version in proposed CI | License | Source |
|---|---|---|---|---|
| CPython | Python interpreter / stdlib in built EXEs | 3.12.x via setup-python | Python Software Foundation License | https://www.python.org/psf/license/ |
| Tcl/Tk | GUI runtime included via tkinter/PyInstaller | bundled with Python runner | Tcl/Tk licenses | https://www.tcl.tk/software/tcltk/license.html |
| tkinterdnd2 | Optional drag-and-drop wrapper | 0.4.3 | MIT | https://pypi.org/project/tkinterdnd2/0.4.3/ |
| TkDND | Native drag-and-drop runtime bundled by tkinterdnd2 | package-specific build | BSD-style (upstream), exact bundled files to confirm | https://github.com/petasis/tkdnd |
| PyInstaller | Freezing and bootloader | 6.22.3 | GPL-2.0 with exception, components may use Apache-2.0 | https://www.pyinstaller.org/en/stable/license.html |

The build-time dependency list includes transitive dependencies. Before signing, run `python -m pip freeze`, create an SPDX or CycloneDX SBOM, inspect bundled wheels and `dist` binaries, and verify the actual license texts and source provenance. For SignPath Foundation, **the absence of proprietary components must be established, not assumed**.

The proposed CI intentionally pins build tools to exact versions. For stronger supply-chain provenance, pin GitHub Actions by reviewed commit SHA and third-party wheels by hashes before final signing. Build reproducibility across Windows hosts is not yet proven.

Commercially licensed or closed source libraries must not be added without explicit licensing review. The three ResoArc scanning modules are ResoArc-authored and MIT licensed.
