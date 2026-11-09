#!/usr/bin/env python3
"""Run preserved historic browser acceptance cases against their matching
immutable site tree, never the later Pages site. SHA-pinned Git ancestry,
fail-closed archive extraction, real Playwright assertions, no test suppression.
"""
import io
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = [
 ("14b9aed61e21c46bb4b2f1e1e099b347476abc52", [
   "tests/pi_site_smoke.py",
   "tests/suite16_release_smoke.py",
   "tests/top_news_sync_smoke.py",
   "tests/catalog_media_smoke.py",
 ]),
 ("cd7cd8416a1d0772cc049c4c612fd458687c0f7e", [
   "tests/site_ux_source_smoke.py",
 ]),
]
def git(*parts):
 return subprocess.run(("git",*parts),cwd=ROOT,check=True,capture_output=True).stdout

def run_snapshot(sha, tests):
 assert git("rev-parse","--verify",sha+"^{commit}").decode().strip()==sha
 git("merge-base","--is-ancestor",sha,"HEAD")
 with tempfile.TemporaryDirectory(prefix="resoarc-browser-history-") as temp:
  root=Path(temp)
  data=git("archive","--format=zip",sha)
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   if z.testzip() is not None:raise ValueError("corrupt historical git archive")
   for name in z.namelist():
    if name.startswith(("/","\\")) or "\\" in name or ".." in name.split("/"):
     raise ValueError("unsafe historical archive path "+name)
   z.extractall(root)
  if sha == SNAPSHOTS[0][0]:
   # The 14b9aed tree intentionally excludes releases; restore only the
   # separately pinned and verified historical GitHub Release archives.
   mirror=ROOT/".historical-release-cache"
   inventory=json.loads((root/"docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json").read_text("utf8"))
   for entry in inventory["assets"]:
    name=entry["filename"]
    original=mirror/name
    if not original.is_file():raise ValueError("missing immutable historical distribution "+name)
    blob=original.read_bytes()
    if len(blob)!=entry["bytes"] or hashlib.sha256(blob).hexdigest()!=entry["sha256"]:
     raise ValueError("historical mirror digest mismatch "+name)
    destination=root/"site/downloads"/name
    if destination.exists():
     if destination.read_bytes()!=blob:raise ValueError("frozen archive collision "+name)
    else:
     destination.parent.mkdir(parents=True,exist_ok=True)
     destination.write_bytes(blob)
  for rel in tests:
   if not (root/rel).is_file():raise ValueError("missing frozen browser test "+rel)
   result=subprocess.run((sys.executable,rel),cwd=root,capture_output=True,text=True,
                         timeout=180,errors="replace")
   if result.returncode:
    print((result.stdout+"\n"+result.stderr)[-2800:],file=sys.stderr)
    raise RuntimeError("historical browser test failed "+sha[:9]+":"+rel)
   print("FROZEN_BROWSER_PASS",sha[:9],rel,flush=True)
if __name__=="__main__":
 for sha,tests in SNAPSHOTS:run_snapshot(sha,tests)
 print("FROZEN_BROWSER_ACCEPTANCE_PASS 5 scripts across 2 immutable snapshots")
