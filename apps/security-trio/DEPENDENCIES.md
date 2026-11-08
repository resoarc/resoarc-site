# Dependencies and supply chain (v0.3.0-rc1)

- **Runtime (source)**: Python 3.10+ standard library, bundled `tkinter`/Tcl/Tk.
- **Optional drag-and-drop**: `tkinterdnd2>=0.4.2,<0.5` (bundles TkDND; only required if DnD is needed).
- **Windows EXE builder**: PyInstaller `6.22.3` (build-time only). For security updates, re-evaluate and pin new versions before final signing.
- **Network use**: the tool's scanning code does not perform HTTP calls; installing packages / CI may use network. No code that uploads scans is included.
- **Distribution**: unsigned builds should remain internal until independent review; SmartScreen warnings must not be bypassed by disabling protections.
- **Third-party review**: not conducted; no independent security certification claimed.
