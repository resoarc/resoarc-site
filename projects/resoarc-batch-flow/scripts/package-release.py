#!/usr/bin/env python3
"""Create reproducible, secret-free ResoArc Clock packages. No uploads."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
import hashlib
import re
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.3.4"
SRC_NAME = f"resoarc-clock-source-v{VERSION}.zip"
KIT_NAME = f"resoarc-clock-kit-v{VERSION}.zip"
SOURCES = [
    "README.md", "LICENSE", "package.json", ".gitignore",
    "src", "tests", "control-app", "center-plugin/src",
    "worker/src", "worker/CLOCK.md", "worker/README.md",
    "worker/center-wrangler.example.jsonc",
    "worker/scripts/verify-live-cron.mjs",
    "docs/REAL-KINTONE-STAGING-E2E-20261017.md",
    "scripts/mr-batch-center-readiness.cjs",
]
INSTALLER = ROOT / "release" / "resoarc-clock-bootstrap-v0.3.4.js"
PLUGIN = ROOT / "center-plugin" / "release" / "resoarc-batch-center-v0.2.1.zip"
DOC = ROOT / "release" / "RELEASE-0.3.4.md"
def collect_files():
    output=[]
    for item in SOURCES:
        root=ROOT/item
        if not root.exists(): raise RuntimeError("Missing source: "+item)
        if root.is_file():output.append(root)
        else:output.extend(path for path in root.rglob("*") if path.is_file())
    output.append(INSTALLER)
    forbidden=(".ppk",".env",".dev.vars",".wrangler",".git/","node_modules/","__pycache__")
    for path in output:
        rel=path.relative_to(ROOT).as_posix()
        if any(bad in rel.lower() for bad in forbidden):
            raise RuntimeError("Refusing potentially private path: "+rel)
        if path.suffix.lower() in {".js",".mjs",".json",".jsonc",".md",".css",".html",".txt"}:
            raw=path.read_bytes()
            if b"C:\\Users\\" in raw or re.search(rb"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", raw):
                raise RuntimeError("Potential identifying text in "+rel)
    return sorted(set(output),key=lambda x:x.relative_to(ROOT).as_posix())
def archive(files):
    buf=BytesIO()
    with ZipFile(buf,"w",compression=ZIP_DEFLATED,compresslevel=9) as z:
        for path in files:
            z.write(path,arcname=path.relative_to(ROOT).as_posix())
    return buf.getvalue()
def verify_package(path):
    with ZipFile(path) as z:
        assert z.testzip() is None, "Corrupt ZIP"
        return len(z.namelist())
def main():
    import subprocess
    subprocess.run(["node","control-app/build-installer.mjs"],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    source_bytes=archive(collect_files())
    out=ROOT/"release"/SRC_NAME
    out.write_bytes(source_bytes)
    with ZipFile(ROOT/"release"/KIT_NAME,"w",compression=ZIP_DEFLATED,compresslevel=9) as z:
        z.write(out,SRC_NAME)
        z.write(PLUGIN,PLUGIN.name)
        z.write(INSTALLER,INSTALLER.name)
        z.write(DOC,"RELEASE-NOTES.md")
    print(json.dumps({
        "source":{"file":out.name,"bytes":out.stat().st_size,"entries":verify_package(out),
                  "sha256":hashlib.sha256(out.read_bytes()).hexdigest()},
        "kit":{"file":KIT_NAME,"bytes":(ROOT/"release"/KIT_NAME).stat().st_size,
               "entries":verify_package(ROOT/"release"/KIT_NAME)},
        "containsSigningPrivateKey":False
    },ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
