#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Independent read-only CRC/SHA/signature/source equality verification for three signed ZIPs."""
import hashlib, io, json, zipfile, re, sys
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

root=Path(__file__).resolve().parents[1]
d=root/"site/downloads"
known={
 "input-template":"d466741e9d8ee554ecbdbe3d4d744fb804e8f5364f4bb213249db3fc8df80c65",
 "reuse-reset":"4b7d1e19637cc69a0895b69ddceb533fcb39e56822c200c1730775261ceae4f9",
 "mail-compose":"1c68772578f2c12e1e98a77e983a0a91932880a7a01b1b4a6350cdaa98ac691e",
}
records=[]
for slug,expected in known.items():
 pkg=d/f"resoarc-{slug}-v1.0.0-20261022.zip"
 src=d/f"resoarc-{slug}-v1.0.0-signed-source.zip"
 package=pkg.read_bytes()
 assert hashlib.sha256(package).hexdigest()==expected,slug
 with zipfile.ZipFile(io.BytesIO(package)) as outer:
  assert outer.testzip() is None
  assert {"contents.zip","PUBKEY","SIGNATURE"} <= set(outer.namelist())
  inner=outer.read("contents.zip")
  pubkey=outer.read("PUBKEY")
  signature=outer.read("SIGNATURE")
  pub=load_der_public_key(pubkey)
  algorithm=None
  for alg in (hashes.SHA256(), hashes.SHA1(), hashes.SHA512()):
   try:
    pub.verify(signature,inner,padding.PKCS1v15(),alg)
    algorithm=alg.name
    break
   except InvalidSignature:
    continue
  assert algorithm is not None, f"Signature could not be verified: {slug}"
  with zipfile.ZipFile(io.BytesIO(inner)) as z:
   assert z.testzip() is None
   manifest=json.loads(z.read("manifest.json"))
   assert manifest["version"]=="1.0.0",slug
   contents=z.namelist()
   assert all(not re.search(r'(^|/)(?:\.env|private\.key|id_rsa|api_token)(?:$|/)',p,re.I) for p in contents)
   runtime_files={name:z.read(name) for name in contents}
 with zipfile.ZipFile(src) as z:
  assert z.testzip() is None
  src_names=z.namelist()
  assert all(name in src_names and z.read(name)==body for name,body in runtime_files.items()),f"Signed runtime/source mismatch: {slug}"
  assert {"LICENSE","NOTICE"} <= set(src_names),slug
 for suffix in ("LICENSE.txt","NOTICE.txt","RELEASE_NOTES.md","INSTALL_MIGRATION_GUIDE.md"):
  doc=d/f"resoarc-{slug}-v1.0.0-{suffix}"
  assert doc.is_file() and doc.stat().st_size>30,doc
 records.append({"slug":slug,"signed_zip_sha256":expected,"signature_verified":True,
   "signature_algorithm":algorithm,"source_zip_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
   "runtime_source_files_exact_match":len(contents),"outer_zip_crc_pass":True,"inner_zip_crc_pass":True,
   "version":manifest["version"],"source_notice_present":True})
 print("PASS",slug,"signature=",algorithm,"runtime/source exact=",len(contents))
print("SIGNED_ARCHIVES_3_PASS cryptographic_signatures_verified=3 source_equality=3")
print(json.dumps(records,ensure_ascii=False,indent=2))
