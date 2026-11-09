#!/usr/bin/env python3
"""Review npm dependency manifests before publishing changes."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "DIRECT_DEPENDENCIES.md").read_text(encoding="utf-8")
tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
packages = sorted(x for x in tracked if x.endswith("/package.json"))
errors = []
if len(packages) != 9:
    errors.append("Expected nine reviewed package.json files; update the inventory")
for relative in packages:
    obj = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if relative not in DOC:
        errors.append("Missing documentation for " + relative)
    if obj.get("dependencies") or obj.get("devDependencies"):
        errors.append("New direct dependencies need a reviewed inventory: " + relative)
print("Direct npm package manifests:", len(packages))
for problem in errors:
    print("FAIL:", problem, file=sys.stderr)
raise SystemExit(1 if errors else 0)
