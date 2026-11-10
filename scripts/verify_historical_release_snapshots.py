#!/usr/bin/env python3
"""Strict, immutable historical release checks in their original Git tree.
Current site assets are never substituted for older QA archives. This verifies
the exact older legal/provenance ledger rather than rewriting old digests.
Requires complete reachable Git history; fails closed if a pin is missing.
This is technical evidence, not independent legal rights signoff.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HISTORIC_COMMIT = "14b9aed61e21c46bb4b2f1e1e099b347476abc52"
ALPHA_SOURCE_COMMIT = "b08042cdbc74f8a741a1e78c752f3bb16ae4e974"
LEGACY_CACHE = ROOT / ".historical-release-cache"
CHECKS = {
    "licenses-35": "scripts/verify_osps_35_license_delivery.py",
    "license-ids-35": "scripts/check_osps_le02_35_osi_licenses.py",
    "web8-frozen": "scripts/verify_web8_v1.py",
    "suite16-frozen": "scripts/verify_suite16_readiness.py",
    "signed-release-license": "scripts/audit_release_license_evidence.py",
    "openchain-frozen": "scripts/verify_openchain_scoped_sbom.py",
}
HISTORIC_ASSETS = {
    "docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json",
    "docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json",
    "docs/compliance/OPENCHAIN_BROWSER_TOOLS_20261106.cdx.json",
}
def invoke(*args, cwd=ROOT, check=True, capture=True):
    return subprocess.run(args, cwd=cwd, check=check, capture_output=capture)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def git_blob(commit,rel):
    return invoke("git","show",f"{commit}:{rel}").stdout
def check_pins():
    for commit in (HISTORIC_COMMIT,ALPHA_SOURCE_COMMIT):
        resolved=invoke("git","rev-parse","--verify",commit+"^{commit}").stdout.decode().strip()
        if resolved!=commit:
            raise ValueError("historical commit identity mismatch: "+commit)
        invoke("git","merge-base","--is-ancestor",commit,"HEAD")
    for rel in HISTORIC_ASSETS:
        original=git_blob(HISTORIC_COMMIT,rel)
        current=ROOT/rel
        if not current.is_file() or current.read_bytes()!=original:
            raise ValueError("historic inventory has been edited in the current branch: "+rel)
def check_alpha_archives():
    slugs=("conditional-format","date-calculator","list-search","grid-editor","kanban")
    count=0
    for slug in slugs:
        zipfile_path=ROOT/f"site/downloads/resoarc-{slug}-v0.1.0-alpha-source.zip"
        if not zipfile_path.is_file():raise ValueError("missing active alpha ZIP "+slug)
        with zipfile.ZipFile(zipfile_path) as z:
            if z.testzip() is not None:raise ValueError("corrupt alpha ZIP "+slug)
            actual=set(z.namelist())
            prefix=f"{slug}-v0.1.0-alpha/"
            for name in actual:
                if not name.startswith(prefix) or not name.endswith("/") and (
                    name.startswith("/") or ".." in name.split("/") or "\\" in name
                ):raise ValueError("unsafe alpha archive path "+name)
                rel=f"plugins/{slug}/v0.1.0-alpha/{name[len(prefix):]}"
                if z.read(name)!=git_blob(ALPHA_SOURCE_COMMIT,rel):
                    raise ValueError("archive differs from original source commit "+name)
                count+=1
            paths=invoke("git","ls-tree","-r","--name-only",ALPHA_SOURCE_COMMIT,
                        f"plugins/{slug}/v0.1.0-alpha").stdout.decode().splitlines()
            expected={prefix+x.split(f"plugins/{slug}/v0.1.0-alpha/",1)[1] for x in paths}
            if actual!=expected:raise ValueError("source archive entry list changed: "+slug)
    print(f"FROZEN_ALPHA_SOURCE_PASS {len(slugs)} plugin archives {count} original files commit {ALPHA_SOURCE_COMMIT}",flush=True)
def check_historical(keys):
    missing=[x for x in CHECKS if x not in keys]
    if not keys:return
    if not LEGACY_CACHE.is_dir():raise RuntimeError("immutable GitHub Release cache not hydrated")
    with tempfile.TemporaryDirectory(prefix="resoarc-frozen-audit-") as directory:
        tmp=Path(directory)
        git_zip=invoke("git","archive","--format=zip",HISTORIC_COMMIT).stdout
        with zipfile.ZipFile(io.BytesIO(git_zip)) as zipped:
            if zipped.testzip() is not None:raise ValueError("historical Git tree ZIP CRC")
            zipped.extractall(tmp)
        # Hydrate archived binary fixtures only within temporary historical checkout.
        # Never copy them over currently published Pages ZIP names.
        historical_manifest=json.loads((tmp/"docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json").read_text("utf8"))
        archive_names={x["filename"] for x in historical_manifest["assets"]}
        for name in archive_names:
            source=LEGACY_CACHE/name
            if not source.is_file():raise RuntimeError("missing immutable archive sidecar "+name)
            shutil.copy2(source,tmp/"site/downloads"/name)
        for row in historical_manifest["assets"]:
            data=(tmp/"site/downloads"/row["filename"]).read_bytes()
            if sha(data)!=row["sha256"] or len(data)!=row["bytes"]:
                raise ValueError("historic Release archive digest mismatch "+row["filename"])
        print("HISTORIC_RELEASE_SNAPSHOT_PINNED",HISTORIC_COMMIT,flush=True)
        for key in sorted(keys):
            result=invoke(sys.executable,CHECKS[key],cwd=tmp,check=False)
            if result.returncode:
                sys.stdout.write(result.stdout.decode("utf8",errors="replace")[-2100:])
                sys.stderr.write(result.stderr.decode("utf8",errors="replace")[-2100:])
                raise RuntimeError(f"historical {key} failed: {result.returncode}")
            print("FROZEN_EVIDENCE_PASS",key,flush=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="append",choices=sorted(CHECKS)+["alpha"])
    args=p.parse_args()
    checks=args.check or list(CHECKS)+["alpha"]
    check_pins()
    if "alpha" in checks:check_alpha_archives()
    check_historical({c for c in checks if c!="alpha"})
    print("IMMUTABLE_RELEASE_PROVENANCE_PASS",len(checks),"checks",flush=True)
if __name__=="__main__":
    try:main()
    except Exception as ex:
        print("IMMUTABLE_RELEASE_PROVENANCE_FAIL",type(ex).__name__,str(ex),file=sys.stderr)
        sys.exit(1)
