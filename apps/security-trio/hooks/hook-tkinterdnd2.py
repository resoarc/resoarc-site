"""PyInstaller hook for tkinterdnd2 0.4.3 on Windows x64 only.

Do not collect_all() platform-specific native TkDND code: the wheel includes
macOS, Linux, Windows x86, and Windows ARM64 binaries that are not used here.
"""
from __future__ import annotations

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

if sys.platform != "win32":
    raise RuntimeError("Security Trio distribution hook supports only Windows x64")

# Includes pkgIndex.tcl and supporting Tcl scripts for this exact wheel layout.
datas = collect_data_files("tkinterdnd2", includes=["tkdnd/win-x64/**"])
binaries = [
    (source, dest)
    for source, dest in collect_dynamic_libs("tkinterdnd2")
    if dest.replace("\\", "/").lower().endswith("/tkdnd/win-x64")
]
if len(binaries) != 1 or not any(source.lower().endswith(".dll") for source, _ in binaries):
    raise RuntimeError("Unexpected tkinterdnd2 TkDND wheel layout: expected one win-x64 DLL")
if not any(source.lower().endswith("pkgindex.tcl") for source, _ in datas):
    raise RuntimeError("Unexpected tkinterdnd2 TkDND wheel layout: pkgIndex.tcl missing")
