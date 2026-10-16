#!/usr/bin/env python3
"""ResoArc suite 16-feature release gate: offline, reproducible, no private keys."""
from __future__ import annotations
import hashlib,io,json,re,sys,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
PLUGINS={
"auto-number":"v1.1.0-beta","tabs":"v0.1.0-beta","conditional":"v0.1.0-alpha",
"conditional-format":"v0.1.0-alpha","date-calculator":"v0.1.0-alpha",
"list-search":"v0.1.0-alpha","grid-editor":"v0.1.0-alpha","kanban":"v0.1.0-alpha"}
WEB=["kintone-bulk-preview","kintone-app-diff","kintone-permission-audit",
"kintone-import-check","kintone-duplicates","kintone-lookup-audit",
"kintone-cross-aggregate","kintone-print-report"]
def abort(message):raise ValueError(message)
def verify():
 published=json.loads((SITE/"downloads/resoarc-signed-qa-manifest.json").read_text(encoding="utf8"))
 assert published["notice"]=="SIGNED_QA_ONLY_NOT_TENANT_TESTED"
 items=published["plugins"]
 assert len(items)==8 and set(x["slug"] for x in items)==set(PLUGINS)
 ids=set()
 for item in items:
  slug=item["slug"]
  root=ROOT/"plugins"/slug/PLUGINS[slug]/"src"
  manifest=json.loads((root/"manifest.json").read_text(encoding="utf8"))
  assert manifest["type"]=="APP",slug
  assert all(k in manifest for k in ("name","desktop","config"))
  assets=set()
  for section in ("desktop","mobile","config"):
   val=manifest.get(section,{})
   for key in ("js","css"):
    for name in val.get(key,[]):
     assert not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts,(slug,name)
     assert (root/name).is_file(),(slug,name)
     assets.add(name)
   for key in ("html","icon"):
    if key in val and isinstance(val[key],str):
     assert (root/val[key]).is_file(),(slug,val[key])
     assets.add(val[key])
  assert (root/manifest["icon"]).is_file(),slug
  assert not re.search(r"PRIVATE KEY|BEGIN RSA PRIVATE",json.dumps(manifest)),slug
  file=SITE/"downloads"/item["filename"]
  assert item["filename"]==f"resoarc-{slug}-signed-qa.zip"
  assert hashlib.sha256(file.read_bytes()).hexdigest()==item["sha256"],slug
  assert 0<file.stat().st_size==item["bytes"]<500000,slug
  assert re.fullmatch(r"[a-p]{32}",item["plugin_id"]),slug
  assert item["plugin_id"] not in ids,slug
  ids.add(item["plugin_id"])
  with zipfile.ZipFile(file) as z:
   assert set(z.namelist())=={"contents.zip","PUBKEY","SIGNATURE"},slug
   assert len(z.read("PUBKEY"))>=100 and len(z.read("SIGNATURE"))>=100,slug
   with zipfile.ZipFile(io.BytesIO(z.read("contents.zip"))) as inner:
    names=set(inner.namelist())
    assert names == assets|{"manifest.json",manifest["icon"]},(slug,sorted(names^(assets|{"manifest.json",manifest["icon"]})))
    for name in names:
     assert ".." not in PurePosixPath(name).parts and not name.startswith("/"),(slug,name)
     assert inner.read(name)==(root/name).read_bytes(),(slug,name)
  route=SITE/"tools"/f"kintone-{slug}"/"index.html"
  assert route.is_file(),slug
  print(f"QA plugin: {slug:22s} signed source match")
 for slug in WEB:
  path=SITE/"tools"/slug/"index.html"
  assert path.is_file(),slug
  html=path.read_text(encoding="utf8")
  assert "<main" in html and "ResoArc" in html,slug
  print(f"Web utility: {slug:28s} route OK")
 page=(SITE/"products/kintone/qa/index.html").read_text(encoding="utf8")
 assert "本番投入禁止" in page and all(x["filename"] in page for x in items)
 assert "8機能" in page
 assert all(not list(ROOT.rglob("*.ppk")) for _ in [0]),"PRIVATE SIGNING KEY INSIDE REPO"
 print("SUITE16_RELEASE_GATE_PASS 8 plugins + 8 browser tools; signed QA only, tenant acceptance pending")

if __name__=="__main__":
 try:verify()
 except (OSError,ValueError,AssertionError,zipfile.BadZipFile,KeyError) as e:
  print("SUITE16_RELEASE_GATE_FAIL",e,file=sys.stderr);sys.exit(1)
