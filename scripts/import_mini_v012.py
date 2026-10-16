#!/usr/bin/env python3
"""ResoArc v0.1.2 source import: immutable original, fail-closed, no keys and no deployment.
Safe unattended command on the owner's PC once the source ZIP has been placed in Downloads
or Documents/AI-Work/MR-kintone-tests/inbox. No environment secrets read.
"""
import json, hashlib, os, sys, zipfile, shutil, tempfile, stat
from pathlib import Path

HOME=Path.home()
BASE=HOME/"Documents"/"AI-Work"/"MR-kintone-tests"
TARGET=HOME/"Documents"/"GitHub"/"resoarc-mini-plugins"
SOURCE_NAME="resoarc-mini-plugins-v0.1.2-source.zip"
SOURCE_SHA="22f22159407063a90fc354cf0ee1af1283f402f25fe554d5f7c49026a4da0edb"
SLUGS=set("""input-template reuse-reset text-normalizer field-help save-navigation mail-compose list-aggregate csv-export attachment-count table-row-tools qr-code record-toc related-links sticky-list file-preview lookup-suggest postal-address barcode-scan""".split())
INBOXES=[BASE/"inbox",HOME/"Downloads", HOME/"Documents"/"AI-Work"/"ResoArc"/"inbox",TARGET]
REPORT=BASE/"reports"/"mini-source-import-20261017.json"

def fail(reason):
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({"ok":False,"status":"blocked","reason":reason,"source":SOURCE_NAME},ensure_ascii=False,indent=2),encoding="utf-8")
    print("SOURCE_IMPORT_BLOCKED:",reason)
    raise SystemExit(2)

found=[p/SOURCE_NAME for p in INBOXES if (p/SOURCE_NAME).is_file()]
if not found:
    fail("v0.1.2 source ZIP not on PC yet. Place original ZIP in " + str(INBOXES[0]))
source=found[0]
digest=hashlib.sha256(source.read_bytes()).hexdigest()
if digest != SOURCE_SHA:
    fail("SHA-256 mismatch. Do not install an unknown ZIP")
with zipfile.ZipFile(source) as z:
    entries=[m for m in z.infolist() if not m.is_dir()]
    if len(entries)!=152:fail(f"Unexpected source file count: {len(entries)}, expected 152")
    names=[m.filename for m in entries]
    if len(set(names))!=len(names):fail("Duplicate paths in ZIP")
    manifests=set()
    for m in entries:
        path=Path(m.filename)
        if (m.filename.startswith("/") or "\\" in m.filename or
            ".." in path.parts or ":" in m.filename or not path.parts or
            (m.external_attr >> 16) & stat.S_IFMT(stat.S_IFLNK) == stat.S_IFLNK):
            fail("Unsafe ZIP entry")
        if m.file_size>2_000_000:fail("Unexpectedly large ZIP member")
        if len(path.parts)==3 and path.parts[0]=="plugins" and path.parts[2]=="manifest.json":
            manifests.add(path.parts[1])
    if manifests != SLUGS:fail("Manifest set mismatch")
    if sum(m.file_size for m in entries)>10_000_000:fail("Uncompressed size too large")
    if TARGET.exists() and list(TARGET.iterdir()):
        marker=TARGET/"import-evidence.json"
        if marker.is_file():
            try:
                doc=json.loads(marker.read_text(encoding="utf-8"))
                if doc.get("source_sha256")==SOURCE_SHA:
                    print("SOURCE_IMPORT_ALREADY_VERIFIED",TARGET)
                    raise SystemExit(0)
            except (ValueError,UnicodeError): pass
        fail("Destination is NOT empty; refusing overwrite: " + str(TARGET))
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    # Avoid partial source tree becoming the trusted source on extraction failure.
    stage=Path(tempfile.mkdtemp(prefix="resoarc-v012-",dir=str(TARGET.parent)))
    try:
        for m in entries:
            dst=stage/Path(m.filename)
            dst.parent.mkdir(parents=True,exist_ok=True)
            with z.open(m) as inp, dst.open("wb") as out: shutil.copyfileobj(inp,out)
        if TARGET.exists():TARGET.rmdir()  # confirmed empty above
        stage.rename(TARGET)
    except BaseException:
        shutil.rmtree(stage,ignore_errors=True)
        raise
report={"ok":True,"status":"original_source_imported","source_name":SOURCE_NAME,
        "source_sha256":SOURCE_SHA,"files":len(entries),"plugins":len(SLUGS),
        "target":str(TARGET),"signed_zip_imported":False,"v1_release_approved":False,
        "note":"Original source archive only, no private signing keys or production publishing."}
(TARGET/"import-evidence.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
REPORT.parent.mkdir(parents=True,exist_ok=True)
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("SOURCE_IMPORT_OK",str(TARGET))
