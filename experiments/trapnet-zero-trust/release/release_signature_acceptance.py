#!/usr/bin/env python3
"""Offline release trust-chain acceptance using *only synthetic* test artifacts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

NAMES=("guardian-linux-amd64","guardian-linux-arm64","guardian-windows-amd64.exe")
def run(argv,cwd):
    return subprocess.run(list(map(str,argv)),cwd=cwd,capture_output=True,text=True,timeout=35)
def verify(source):
    source=Path(source).resolve()
    checks=[]
    def check(name,condition):
        checks.append({"name":name,"passed":bool(condition)})
        if not condition:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="trapnet-release-signature-") as d:
        temp=Path(d)
        suffix=".exe" if os.name=="nt" else ""
        tools={}
        for name in ("keygen","release-sign","release-verify"):
            dest=temp/(name+suffix)
            check("build_"+name,run(["go","build","-trimpath","-o",dest,"./cmd/"+name],source).returncode==0)
            tools[name]=dest
        key=temp/"publisher-test-key"
        stranger=temp/"other-publisher-test-key"
        check("generate_ephemeral_publisher",run([tools["keygen"],"-out",key],source).returncode==0)
        check("generate_ephemeral_other",run([tools["keygen"],"-out",stranger],source).returncode==0)
        bundle=temp/"bundle"
        bundle.mkdir()
        entries=[]
        for name in NAMES:
            payload=("FAKE test bytes only: "+name).encode()
            (bundle/name).write_bytes(payload)
            entries.append({"name":name,"sha256":hashlib.sha256(payload).hexdigest(),"size":len(payload)})
        now=datetime.now(timezone.utc)
        meta={"schema":"trapnet.guardian-release.v1","release":"v0.16.0-beta.1",
              "source_commit_sha":"0123456789abcdef0123456789abcdef01234567",
              "issued_at":(now-timedelta(minutes=1)).isoformat(),
              "expires_at":(now+timedelta(hours=1)).isoformat(),
              "files":entries}
        raw=temp/"manifest.json"
        raw.write_text(json.dumps(meta))
        signed=temp/"signed.json"
        check("root_offline_signature",run([tools["release-sign"],"-manifest",raw,"-key",key/"private.hex","-out",signed],source).returncode==0)
        def inspect(pub=key/"public.hex"):
            return run([tools["release-verify"],"-signed",signed,"-pub",pub,"-bundle",bundle],source)
        check("valid_three_artifacts_verified",inspect().returncode==0)
        check("different_publisher_key_rejected",inspect(stranger/"public.hex").returncode!=0)
        with (bundle/NAMES[0]).open("ab") as file:file.write(b"tampered")
        check("binary_digest_change_rejected",inspect().returncode!=0)
        (bundle/NAMES[0]).write_bytes(("FAKE test bytes only: "+NAMES[0]).encode())
        (bundle/"extra.file").write_bytes(b"unexpected")
        check("unexpected_bundle_file_rejected",inspect().returncode!=0)
        (bundle/"extra.file").unlink()
        original=json.loads(signed.read_text())
        original["manifest"]["source_commit_sha"]="abcdef0123456789abcdef0123456789abcdef01"
        signed.write_text(json.dumps(original))
        check("signed_source_commit_tamper_rejected",inspect().returncode!=0)
        original["manifest"]["release"]="v0.16.0-beta.2"
        signed.write_text(json.dumps(original))
        check("manifest_version_tamper_rejected",inspect().returncode!=0)
    return {"schema":"trapnet.release-signature-test.v1","passed":sum(x["passed"] for x in checks),
            "total":len(checks),"checks":checks,"temporary_signing_keys_removed":True,
            "artifacts_were_synthetic":True,"production_signature_issued":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--source",default=".")
    ap.add_argument("--output");args=ap.parse_args()
    try:
        result=verify(args.source)
        text=json.dumps(result,indent=2)+"\n"
        if args.output:Path(args.output).write_text(text)
        print(text,end="")
    except Exception as err:
        print("release authenticity trial FAILED:",type(err).__name__,str(err),file=sys.stderr)
        sys.exit(1)
