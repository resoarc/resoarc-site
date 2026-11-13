#!/usr/bin/env python3
"""Enforce immutable, exact-byte nontext inventory with technical provenance.
No exemptions by extension alone: archives are allowed only as individually
hash-pinned, cryptographically verified signed distributions or safe source
archives in site/downloads. Historical reviewed graphics list is unchanged.
Passing is NOT independent copyright/third-party-license certification.
"""
from __future__ import annotations
import io, hashlib, json, re, subprocess, sys, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HISTORICAL=ROOT/"docs/compliance/BINARY_ASSET_REVIEW_20261106.json"
ACTIVE=ROOT/"docs/compliance/ACTIVE_PAGES_BINARY_INVENTORY_20261109.json"
PROHIBITED={".exe",".dll",".iso",".jar",".class",".wasm",
            ".o",".a",".so",".dylib",".app",".bin",".rom",".pyc"}
SIGNATURE_MEMBERS={"contents.zip","PUBKEY","SIGNATURE"}
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def kind(data:bytes)->str|None:
 if data.startswith(b"\x89PNG\r\n\x1a\n"):return "png"
 if data.startswith(b"RIFF") and data[8:12]==b"WEBP":return "webp"
 if data.startswith(b"\xff\xd8"):return "jpeg"
 if data.startswith(b"\x00\x00\x01\x00"):return "ico"
 if data.startswith(b"wOF2"):return "woff2"
 if data.startswith(b"PK\x03\x04"):return "zip"
 return None
def validate_archive(blob:bytes,record:dict)->None:
 with zipfile.ZipFile(io.BytesIO(blob)) as z:
  if z.testzip() is not None:raise ValueError("ZIP CRC error")
  names=z.namelist()
  if not names or len(names)!=record["zipEntryCount"] or len(names)!=len(set(names)):
   raise ValueError("entry count or duplicate ZIP paths")
  for name in names:
   if (name.startswith(("/","\\")) or "\\" in name or
       name.endswith("/") and name.replace("/","")!="" and
       any(x==".." for x in name.split("/")) or
       any(x==".." for x in name.split("/")) or "\x00" in name):
    raise ValueError("unsafe ZIP member path")
   if z.getinfo(name).file_size>40_000_000:
    raise ValueError("oversized individual ZIP member")
  signed=set(names)==SIGNATURE_MEMBERS
  if signed != record["containsSignedKintonePayload"]:
   raise ValueError("signature wrapper type changed")
  if signed:
   payload=z.read("contents.zip")
   if sha(payload)!=record["payloadSHA256"] or sha(z.read("PUBKEY"))!=record["publicKeySHA256"]:
    raise ValueError("signed payload/key no longer matches pinned hashes")
   with zipfile.ZipFile(io.BytesIO(payload)) as inner:
    if inner.testzip() is not None or "manifest.json" not in inner.namelist():
     raise ValueError("signed payload invalid")
   # Verify RSA PKCS1v1.5 SHA1 required by the established kintone
   # signing format; never rely only on the existence of SIGNATURE bytes.
   from cryptography.hazmat.primitives.serialization import load_der_public_key
   from cryptography.hazmat.primitives.asymmetric import padding
   from cryptography.hazmat.primitives import hashes
   public=load_der_public_key(z.read("PUBKEY"))
   public.verify(z.read("SIGNATURE"),payload,padding.PKCS1v15(),hashes.SHA1())
def audit()->list[str]:
 problems=[]
 historical=json.loads(HISTORICAL.read_text(encoding="utf8"))
 active=json.loads(ACTIVE.read_text(encoding="utf8"))
 older={x["path"]:x for x in historical["assets"]}
 newer={x["path"]:x for x in active["assets"]}
 if len(older)!=34:problems.append("historical 34 reviewed assets changed")
 # The two ResoArc Sheet beta archives were individually hash- and ZIP-verified.
 if len(newer)!=86:problems.append("active distribution inventory count drifted")
 if len(set(older)&set(newer)):problems.append("overlapping immutable inventories")
 tracked=subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines()
 for rel in tracked:
  p=ROOT/rel
  if not p.is_file():
   problems.append("missing tracked source file "+rel);continue
  data=p.read_bytes()
  suffix=p.suffix.lower()
  if suffix in PROHIBITED or data.startswith((b"\x7fELF",b"MZ")):
   problems.append("forbidden executable/source binary "+rel)
  typ=kind(data)
  if rel in older:
   x=older[rel]
   if (typ!=x["format"] or len(data)!=x["size"] or sha(data)!=x["sha256"]):
    problems.append("immutable historical reviewed image changed "+rel)
   continue
  if rel in newer:
   x=newer[rel]
   if (typ!=x["type"] or len(data)!=x["size"] or sha(data)!=x["sha256"]):
    problems.append("active site resource changed from pinned review "+rel)
    continue
   if not x.get("reuseLicenseExpressions") or x.get("legalApprovalNotInferred") is not True:
    problems.append("license/provenance annotation missing "+rel)
   if x["type"]=="zip":
    if not re.fullmatch(r"site/downloads/[a-zA-Z0-9._-]+\.zip",rel):
     problems.append("archive outside public distribution boundary "+rel)
    try:validate_archive(data,x)
    except (ValueError,KeyError,zipfile.BadZipFile,ImportError,AssertionError,Exception) as e:
     problems.append("distribution archive verification failure "+rel+": "+type(e).__name__+": "+str(e)[:150])
   elif not rel.startswith("site/assets/"):
    problems.append("graphics outside reviewed static assets "+rel)
   continue
  if typ is not None or b"\x00" in data[:4096]:
   problems.append("unreviewed binary source file "+rel)
 missing=(set(older)|set(newer))-set(tracked)
 if missing:problems.append("missing pinned reviewed files "+", ".join(sorted(missing)[:10]))
 if sum(x["type"]=="zip" for x in newer.values())!=51:
  problems.append("active published ZIP list changed without provenance")
 return problems
if __name__=="__main__":
 try:issues=audit()
 except Exception as exc:
  issues=["auditor exception "+type(exc).__name__+": "+str(exc)]
 for issue in issues:print("FAIL:",issue,file=sys.stderr)
 print("Immutable binary verification: 34 historical reviewed assets + 86 active site distributions; issues",len(issues))
 print("This is byte/format/signature/declared-license evidence, NOT legal rights conformance.")
 raise SystemExit(1 if issues else 0)
