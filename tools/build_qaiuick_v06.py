#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Build immutable qAIUIck v0.6 source distribution with SQLite local backend."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import json

root = Path(__file__).resolve().parents[1]
site = root / "site"
old = site / "downloads/qaiuick-v0.5-beta-source.zip"
new = site / "downloads/qaiuick-v0.6-beta-source.zip"
before = "qAIUIck-v0.5-beta/"
after = "qAIUIck-v0.6-beta/"
files = {}
with ZipFile(old) as previous:
    if previous.testzip() is not None:
        raise RuntimeError("Previous archive failed verification")
    for name in previous.namelist():
        if not name.startswith(before) or name.endswith("/"):
            raise RuntimeError("Unexpected v0.5 archive item")
        path = after + name[len(before):]
        data = previous.read(name)
        if path == after + "package.json":
            package = json.loads(data.removesuffix(bytes((92, 110))))
            package["version"] = "0.6.0"
            package["scripts"]["check"] += " && node --check src/remote.js"
            data = (json.dumps(package, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if path == after + "README.md":
            data = data.decode("utf-8").replace("v0.5", "v0.6").encode("utf-8")
        files[path] = data

for name in ("quick.js", "spec.js", "define.js", "remote.js"):
    files[after + "src/" + name] = (site / "assets/qaiuick" / name).read_bytes()
for name in ("__init__.py", "storage.py", "server.py", "cli.py"):
    files[after + "qaiuick_local/" + name] = (root / "qaiuick_local" / name).read_bytes()
for name in ("index.html", "main.js", "spec.js", "spec.snapshot.json"):
    files[after + "examples/sqlite-inventory/" + name] = (
        root / "examples/sqlite-inventory" / name).read_bytes()
files[after + "docs/SQLITE.md"] = (root / "docs/QAIUICK_SQLITE.md").read_bytes()
files[after + "README.md"] += (
    "\n\n## v0.6: local SQLite (Python standard library)\n\n"
    "Start a loopback-only server from the extracted package folder:\n\n"
    "    python -m qaiuick_local.server --root . --db ../qaiuick-data.sqlite3 --port 8765\n\n"
    "Open http://127.0.0.1:8765/examples/sqlite-inventory/ in a browser.\n"
    "The UI is derived from one spec with storage: 'sqlite'.\n"
    "See docs/SQLITE.md for online backup, restore-to-new, export/import, safety and limits.\n"
    "Existing v0.5 APIs are unchanged; prior ZIPs are retained.\n"
).encode("utf-8")

with ZipFile(new, "w", compression=ZIP_DEFLATED, compresslevel=9) as zip_file:
    for name, data in sorted(files.items()):
        info = ZipInfo(name, date_time=(2026, 11, 10, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        zip_file.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)
data = new.read_bytes()
digest = sha256(data).hexdigest()
(new.with_suffix(new.suffix + ".sha256")).write_text(
    f"{digest}  {new.name}\n", encoding="ascii", newline="\n")
with ZipFile(new) as check:
    assert check.testzip() is None
    assert check.read(after + "src/remote.js") == (site / "assets/qaiuick/remote.js").read_bytes()
    assert len(check.namelist()) == len(files)
    assert json.loads(check.read(after + "package.json"))["version"] == "0.6.0"
print("QAIUICK_V06_ZIP_PASS", len(files), "files", len(data), "bytes", digest)
