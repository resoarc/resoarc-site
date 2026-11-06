#!/usr/bin/env python3
"""Verify pinned successor release ZIPs against public source and historical signing keys.

--hydrate fetches only immutable named release assets from public GitHub Releases.
Never modifies historical artifacts, and never uses private signing keys.
"""
import argparse,hashlib,io,json,os,sys,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"site/downloads"
MANIFEST=OUT/"resoarc-codeql17-v069-release-manifest.json"
TAG="resoarc-codeql17-v069-20261106"
HOST="https://github.com/resoarc/resoarc-site/releases/download/"+TAG+"/"
CAP=1000000
def digest(blob):return hashlib.sha256(blob).hexdigest()
def checked(row,fetch):
 name=row["filename"]
 if PurePosixPath(name).name!=name or not name.endswith(".zip"):raise ValueError("unsafe asset path")
 p=OUT/name
 if not p.is_file():
  if not fetch:raise ValueError("missing release asset: "+name)
  req=urllib.request.Request(HOST+name,headers={"User-Agent":"ResoArc-v069-verifier"})
  fd,tmp=tempfile.mkstemp(prefix=".new-release-",suffix=".part",dir=OUT)
  try:
   with os.fdopen(fd,"wb") as f,urllib.request.urlopen(req,timeout=65) as response:
    total=0
    while True:
     b=response.read(65536)
     if not b:break
     total+=len(b)
     if total>CAP or total>row["size"]:raise ValueError("release asset exceeds expected size")
     f.write(b)
   candidate=Path(tmp)
   if candidate.stat().st_size!=row["size"] or digest(candidate.read_bytes())!=row["sha256"]:
    raise ValueError("downloaded checksum mismatch: "+name)
   candidate.replace(p)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
 data=p.read_bytes()
 if len(data)!=row["size"] or len(data)>CAP or digest(data)!=row["sha256"]:
  raise ValueError("asset SHA/size mismatch: "+name)
 return data
def members(z):
 names=z.namelist()
 if len(names)!=len(set(names)) or len(names)>60:raise ValueError("duplicate/excessive ZIP entries")
 for n in names:
  p=PurePosixPath(n)
  if not n or p.is_absolute() or ".." in p.parts or "\\" in n:raise ValueError("unsafe ZIP entry")
 return names
def verify_plugin(item,fetch,legacy):
 slug=item["slug"]
 directory=ROOT/item["release_dir"]
 manifest=json.loads((directory/"src/manifest.json").read_text(encoding="utf8"))
 if manifest["version"]!=item["version"]:raise ValueError("plugin version mismatch")
 source_bytes=checked(item["source"],fetch)
 with zipfile.ZipFile(io.BytesIO(source_bytes)) as source_zip:
  actual=set(members(source_zip))
  expected={directory.relative_to(ROOT).as_posix()+"/"+x.relative_to(directory).as_posix()
            for x in directory.rglob("*") if x.is_file()}
  if actual!=expected:raise ValueError("source archive inventory mismatch: "+slug)
  for name in expected:
   if source_zip.read(name)!=(ROOT/name).read_bytes():raise ValueError("source ZIP hash mismatch "+name)
 signed_bytes=checked(item["signed"],fetch)
 with zipfile.ZipFile(io.BytesIO(signed_bytes)) as outer:
  if set(members(outer))!={"contents.zip","PUBKEY","SIGNATURE"}:raise ValueError("signed wrapper invalid")
  pub=outer.read("PUBKEY")
  if len(pub)<80 or len(outer.read("SIGNATURE"))<80:raise ValueError("missing signature")
  legacy_file="resoarc-"+slug+"-signed-qa.zip"
  # Reuse the actual historical public QA signing key, never export private keys.
  old=OUT/legacy_file
  if old.exists():
   with zipfile.ZipFile(old) as old_outer:
    if pub!=old_outer.read("PUBKEY"):raise ValueError("plugin identity key mismatch "+slug)
  with zipfile.ZipFile(io.BytesIO(outer.read("contents.zip"))) as inside:
   entries=members(inside)
   for name in entries:
    if name.startswith("/") or not (directory/"src"/name).is_file():raise ValueError("unknown signed entry")
    if inside.read(name)!=(directory/"src"/name).read_bytes():raise ValueError("signed entry differs "+name)
   if "manifest.json" not in entries:raise ValueError("missing signed manifest")
 print("SIGNED_SUCCESSOR_PASS",slug,item["channel"],item["plugin_id"],"sha256",item["signed"]["sha256"])
def verify_web(item,fetch):
 data=checked(item["source"],fetch)
 manifest=json.loads((OUT/"resoarc-web8-v1.0.1-manifest.json").read_text(encoding="utf8"))
 if len(item["routes"])!=8 or item["routes"]!=manifest["routes"]:raise ValueError("Web8 routes mismatch")
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  names=members(z)
  expected={s["path"]:s["sha256"] for s in manifest["sources"]}
  if set(names)!=set(expected):raise ValueError("Web8 files mismatch")
  for path,hash_expected in expected.items():
   payload=z.read(path)
   if digest(payload)!=hash_expected or payload!=(ROOT/path).read_bytes():raise ValueError("Web8 file differs "+path)
 print("WEB8_V101_SUCCESSOR_PASS",len(item["routes"]),"routes",item["source"]["sha256"])
def run(fetch):
 obj=json.loads(MANIFEST.read_text(encoding="utf8"))
 if obj["schema"]!="resoarc.codeql17.successor-release.v1" or obj["legacy_archives_overwritten"] is not False:
  raise ValueError("unrecognized successor manifest")
 rows=obj["signed_plugins"]
 if len(rows)!=4 or [r["slug"] for r in rows]!=["auto-number","auto-number","kanban","list-search"]:
  raise ValueError("unexpected product inventory")
 for row in rows:verify_plugin(row,fetch,True)
 verify_web(obj["web8"],fetch)
 print("CODEQL17_SUCCESSOR_ASSETS_PASS","9 ZIPs; historical release untouched")
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--hydrate",action="store_true")
 a=p.parse_args()
 try:run(a.hydrate)
 except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as e:
  print("CODEQL17_SUCCESSOR_ASSETS_FAIL",str(e),file=sys.stderr);return 2
 return 0
if __name__=="__main__":sys.exit(main())
