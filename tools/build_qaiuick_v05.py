#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Reproducibly assemble v0.5 on top of the immutable v0.4 source ZIP."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import json

root = Path(__file__).resolve().parents[1]
site = root / "site"
old = site / "downloads/qaiuick-v0.4-beta-source.zip"
target = site / "downloads/qaiuick-v0.5-beta-source.zip"
prev = "qAIUIck-v0.4-beta/"
prefix = "qAIUIck-v0.5-beta/"
files = {}
with ZipFile(old) as src:
    if src.testzip() is not None:
        raise ValueError("Previous archive is corrupt")
    for name in src.namelist():
        if not name.startswith(prev) or name.endswith("/"):
            raise ValueError("Unexpected v0.4 path: " + name)
        path = prefix + name.removeprefix(prev)
        data = src.read(name)
        if path == prefix + "README.md":
            data = data.decode("utf-8").replace("v0.4", "v0.5").encode("utf-8")
        if path == prefix + "package.json":
            cfg = json.loads(data.removesuffix(bytes((92, 110))))
            cfg["version"] = "0.5.0"
            data = (json.dumps(cfg, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        files[path] = data

for item in ("spec.js", "define.js", "define.css"):
    files[prefix + "src/" + item] = (site / "assets/qaiuick" / item).read_bytes()
files[prefix + "docs/SPEC_FIRST.md"] = (root / "docs/QAIUICK_SPEC_FIRST.md").read_bytes()
cli = (root / "tools/qaiuick_spec.mjs").read_text("utf-8")
cli = cli.replace("../site/assets/qaiuick/spec.js", "../src/spec.js")
files[prefix + "tools/qaiuick_spec.mjs"] = cli.encode("utf-8")
for slug in ("inventory", "tickets"):
    sub = prefix + "examples/spec-" + slug + "/"
    origin = site / "assets/qaiuick-spec"
    files[sub + "spec.js"] = (origin / (slug + ".spec.js")).read_bytes()
    files[sub + "baseline.json"] = (origin / ("baseline-" + slug + ".json")).read_bytes()
    files[sub + "current.json"] = (origin / ("current-" + slug + ".json")).read_bytes()
    files[sub + "main.js"] = (
        "import { defineApp } from '../../src/define.js';\n"
        "import { spec } from './spec.js';\n"
        "defineApp({ ...spec, baseline: './baseline.json' });\n"
    ).encode("utf-8")
files[prefix + "README.md"] += (
    "\n\n## v0.5: forms, record details and AI change impact\n\n"
    "Declare 'ui.sections' to group input fields; 'ui.detail' to generate a details view.\n"
    "Use 'integer', 'unique', 'minLength', 'maxLength' and 'hint' in field definitions.\n"
    "The CLI 'diff' command prints which UI/data areas changed and recommended tests.\n"
    "See docs/SPEC_FIRST.md and both examples/spec-* directories for runnable samples.\n"
).encode("utf-8")

with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=9) as out:
    for name, data in sorted(files.items()):
        info = ZipInfo(name, date_time=(2026, 11, 10, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        out.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)

raw = target.read_bytes()
digest = sha256(raw).hexdigest()
(target.with_suffix(target.suffix + ".sha256")).write_text(
    f"{digest}  {target.name}\n", "ascii", newline="\n")
with ZipFile(target) as check:
    assert check.testzip() is None
    assert len(check.namelist()) == len(files)
    assert json.loads(check.read(prefix + "package.json"))["version"] == "0.5.0"
    assert check.read(prefix + "src/define.js") == (site / "assets/qaiuick/define.js").read_bytes()
print("QAIUICK_V05_PACKAGE_OK", len(files), "files", len(raw), "bytes", digest)
