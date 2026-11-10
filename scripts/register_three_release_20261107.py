#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Review-scoped exact-path metadata registration for three already signed ZIPs.
Never rebuild or alter the signed package bytes, signature, or original registry entries.
"""
from pathlib import Path
import importlib.util
import json

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("signed_inventory", root/"scripts/check_signed_archive_notice.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
paths = [
 "site/downloads/resoarc-input-template-v1.0.0-20261022.zip",
 "site/downloads/resoarc-reuse-reset-v1.0.0-20261022.zip",
 "site/downloads/resoarc-mail-compose-v1.0.0-20261022.zip",
]
expected = {
 paths[0]:"d466741e9d8ee554ecbdbe3d4d744fb804e8f5364f4bb213249db3fc8df80c65",
 paths[1]:"4b7d1e19637cc69a0895b69ddceb533fcb39e56822c200c1730775261ceae4f9",
 paths[2]:"1c68772578f2c12e1e98a77e983a0a91932880a7a01b1b4a6350cdaa98ac691e",
}
registry = root/"docs/reuse-signed-archive-register.json"
data = json.loads(registry.read_text(encoding="utf-8"))
records = data["files"]
registered = {x["path"]:x for x in records}
actual = mod.current()
assert len(set(registered)) == len(records), "Duplicated registry paths"
assert all(x in actual for x in paths), "Candidate package absent"
for p in paths:
    assert actual[p]["sha256"] == expected[p], (p, actual[p]["sha256"])
    if p in registered:
        assert registered[p]["sha256"] == expected[p], "Previously recorded package changed"
    else:
        records.append(actual[p])
registry.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")

# File-level REUSE 3.3 classification. This is not a substituted rights/notice review
# of archives or a cryptographic validation of outer signatures.
toml = root/"REUSE.toml"
text = toml.read_text(encoding="utf-8")
annotations = [
 ("MIT", [
  "scripts/merge_three_release_20261107.py",
  "scripts/register_three_release_20261107.py",
  "scripts/release_three_archive_audit_20261107.py",
  "tests/kintone_three_browser_release_20261107.py",
  *paths,
  *[f"site/downloads/resoarc-{s}-v1.0.0-{suffix}" for s in
      ("input-template","reuse-reset","mail-compose") for suffix in
      ("INSTALL_MIGRATION_GUIDE.md","LICENSE.txt","NOTICE.txt","RELEASE_NOTES.md","signed-source.zip")],
  "site/products/kintone/input-template/index.html",
  "site/products/kintone/reuse-reset/index.html",
  "site/products/kintone/mail-compose/index.html",
 ]),
 ("LicenseRef-ResoArc-Brand-Art",[
  f"site/assets/kintone-icons/{s}.png" for s in ("input-template","reuse-reset","mail-compose")
 ]),
 ("LicenseRef-ResoArc-Screenshots", [
  f"site/assets/kintone-settings-captures/{s}.webp" for s in ("input-template","reuse-reset","mail-compose")
 ])
]
for lic, files in annotations:
    assert all((root/p).exists() for p in files)
    unregistered = [p for p in files if f'"{p}"' not in text]
    if unregistered:
        text += "\n[[annotations]]\npath = [\n" + "".join(
            "  "+json.dumps(p, ensure_ascii=False)+",\n" for p in unregistered
        ) + ']\nprecedence = "override"\nSPDX-FileCopyrightText = "2026 ResoArc Open Technology Project"\nSPDX-License-Identifier = "'+lic+'"\n'
toml.write_text(text, encoding="utf-8",newline="\n")
print("ADDED_3_SIGNED_PACKAGE_METADATA", len(records), "ARCHIVES_REGISTERED")
print("Signature state: previously fixed package bytes; external license and signature checks remain separate.")
