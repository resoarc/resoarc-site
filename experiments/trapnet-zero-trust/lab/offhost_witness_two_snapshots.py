#!/usr/bin/env python3
"""Synthetic, private, no-public-listener HUB handoff to a DIFFERENT physical host.

MUST run inside a disposable Linux container with --network none. It does
not sign as Witness. All Sensor/HUB private keys stay in temporary memory/files
inside the container and are deleted on exit. Handoff is closed evidence ONLY.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import urllib.error
import urllib.request

URL="http://127.0.0.1:8788"
def call(cmd):
    return subprocess.run([str(x) for x in cmd],capture_output=True,text=True,
                          timeout=30,check=False)
def ready(p):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(90):
        if p.poll() is not None:return False
        try:
            with opener.open(URL+"/health",timeout=.3) as r:
                if r.status==200:return True
        except (urllib.error.URLError,TimeoutError,OSError):
            time.sleep(.1)
    return False
def produce(bindir,outdir,source_sha):
    if not (len(source_sha)==40 and all(c in '0123456789abcdef' for c in source_sha)):
        raise ValueError("unpinned source SHA")
    outdir=Path(outdir)
    if not outdir.is_dir() or list(outdir.iterdir()):
        raise RuntimeError("handoff directory must already exist and be empty")
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1",8788))==0:raise RuntimeError("occupied internal HUB port")
    with TemporaryDirectory(prefix="trapnet-source-signer-") as t:
        root=Path(t)
        node=root/"sensor"
        hubid=root/"hub"
        for directory in (node,hubid):
            r=call([bindir/"keygen","-out",directory])
            if r.returncode:raise RuntimeError("ephemeral keygen failed")
        info=json.loads((node/"node.json").read_text("utf-8"))
        allow=root/"allow.json"
        allow.write_text(json.dumps({info["node_id"]:info["public_key"]}),encoding="utf-8")
        ledger=root/"hub-ledger.jsonl"
        files={
            "sensor-public.hex":(node/"public.hex").read_bytes(),
            "hub-public.hex":(hubid/"public.hex").read_bytes(),
        }
        for index,reason in ((1,"log_corrupt"),(2,"storage_full")):
            pending=root/f"pending-{index}.json"
            offline=call([bindir/"sensor","-key",node/"private.hex",
                  "-gap-reason",reason,"-gap-outbox",pending,
                  "-hub-receipt-pub",hubid/"public.hex"])
            if offline.returncode==0 or not pending.is_file():
                raise RuntimeError("offline original gap not retained")
            original=pending.read_bytes()
            proc=subprocess.Popen([str(bindir/"hub"),"-allowlist",str(allow),
               "-ledger",str(ledger),"-receipt-key",str(hubid/"private.hex")],
               stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                if not ready(proc):raise RuntimeError("disposable HUB unavailable")
                req=urllib.request.Request(URL+"/report",data=original,
                        headers={"Content-Type":"application/json"},method="POST")
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=4) as response:
                    status=response.status
                    receipt=response.read(2049)
                if status!=202 or b'"signature"' not in receipt:
                    raise RuntimeError("signed HUB 202 absent")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=7)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
            if Path(str(ledger)+".lock").exists():
                raise RuntimeError("HUB stale lock")
            snapshot=outdir/f"snapshot-{index}"
            result=call([bindir/"snapshot","-ledger",ledger,"-out",snapshot])
            if result.returncode or not (snapshot/"ledger.jsonl.head").is_file():
                raise RuntimeError("closed consistent snapshot unavailable")
            rows=(snapshot/"ledger.jsonl").read_bytes().count(bytes([10]))
            if rows!=index:raise RuntimeError("ledger row count does not increase")
            files[f"signed-report-{index}.json"]=original
            files[f"signed-hub-receipt-{index}.json"]=receipt
        for name,blob in files.items():
            (outdir/name).write_bytes(blob)
        checksums={}
        snapshots=[f"snapshot-{i}/ledger.jsonl{suffix}" for i in (1,2)
                    for suffix in ("",".head")]
        for name in [*files.keys(),*snapshots]:
            checksums[name]=hashlib.sha256((outdir/name).read_bytes()).hexdigest()
        (outdir/"handoff-manifest.json").write_text(json.dumps({
          "schema":"trapnet.cross-host-handoff.v051","source_commit":source_sha,
          "all_data_synthetic":True,"handoff_contains_private_key":False,
          "producer_network":"container-internal-loopback-only",
          "source_host_role":"HUB-side","accepted_reports":2,
          "snapshot_sequence":[1,2],"sha256":checksums},sort_keys=True),encoding="utf-8")
    return {"stage":"producer","passed":True,"synthetic_only":True,
            "source_commit":source_sha,"handoff_files":len(checksums),
            "keys_exported":False,"host_public_port":False,"snapshots":2}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bin",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--sha",required=True)
    a=p.parse_args()
    try:result=produce(Path(a.bin),Path(a.out),a.sha)
    except Exception as exc:
        result={"stage":"producer","passed":False,"error_class":type(exc).__name__}
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 3
if __name__=="__main__":sys.exit(main())
