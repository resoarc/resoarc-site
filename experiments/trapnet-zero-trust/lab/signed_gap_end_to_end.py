#!/usr/bin/env python3
"""Native localhost-only E2E: corrupt Cowrie-shaped log -> real Sensor -> real HUB.

No public binding, real Cowrie service, live private logs, or network egress.
The probe only targets 127.0.0.1; test refuses an occupied reserved HUB port.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE/"sonar"))
import cowrie_gap_lab_bridge as bridge

HUB_URL="http://127.0.0.1:8788/health"

def cli(args,cwd=HERE,timeout=55):
    return subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,
                          check=False,timeout=timeout)

def lab():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1",8788))==0:
            raise RuntimeError("refuse to run: HUB port already occupied")
    checks=[]
    def check(name,value):
        checks.append({"check":name,"passed":bool(value)})
        if not value:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="trapnet-gap-e2e-") as td:
        root=Path(td);root.chmod(0o700)
        (root/bridge.MARKER).write_bytes(b"DISPOSABLE-ONLY\n")
        keydir=root/"identity"
        binaries=root/"bin";binaries.mkdir(mode=0o700)
        for name in ("keygen","sensor","hub"):
            r=cli(["go","build","-trimpath","-o",binaries/name,"./cmd/"+name])
            check("build_"+name,r.returncode==0)
        keygen=cli([binaries/"keygen","-out",keydir])
        check("ephemeral_identity",keygen.returncode==0)
        info=json.loads((keydir/"node.json").read_text(encoding="utf-8"))
        allow=root/"allowlist.json"
        allow.write_text(json.dumps({info["node_id"]:info["public_key"]}),encoding="utf-8")
        logroot=root/"private-var"
        cowrie=logroot/"log"/"cowrie"
        cowrie.mkdir(parents=True)
        # The filesystem here is deliberately NOT quota-verified. The
        # malformed line itself independently constitutes a real data failure.
        (cowrie/"cowrie.json").write_bytes(b'{"eventid": }\n')
        spool=root/"spool";spool.mkdir(mode=0o700)
        outbox=spool/"pending.json"
        key=keydir/"private.hex"
        sensor=binaries/"sensor"
        dry=bridge.execute(root,logroot,outbox,key,sensor,emit=False)
        check("corruption_classified",dry.get("gap_reason")=="log_corrupt")
        check("default_does_not_send",dry["status"]=="HOLD_MANUAL_SEND_NOT_ARMED" and not outbox.exists())
        initial=bridge.execute(root,logroot,outbox,key,sensor,emit=True)
        check("offline_HUB_HOLD",initial["status"]=="HOLD_PENDING_DELIVERY")
        check("signed_pending_durable",outbox.is_file() and 0<outbox.stat().st_size<=8192)
        original=outbox.read_bytes()
        signed=json.loads(original.decode("utf-8"))
        check("only_typed_gap",signed["report"]["kind"]=="coverage_gap" and signed["report"]["target_port"]==0)
        ledger=root/"hub-ledger.jsonl"
        args=[binaries/"hub","-allowlist",allow,"-ledger",ledger]
        hub=subprocess.Popen(list(map(str,args)),cwd=HERE,stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL)
        try:
            available=False
            for _ in range(50):
                if hub.poll() is not None:break
                try:
                    with urllib.request.urlopen(HUB_URL,timeout=0.5) as resp:
                        if resp.status==200:available=True;break
                except (urllib.error.URLError,TimeoutError,OSError):time.sleep(0.1)
            check("loopback_HUB_ready",available)
            resend=cli([sensor,"-key",key,"-retry-gap-outbox","-gap-outbox",outbox],timeout=15)
            check("same_event_accepted",resend.returncode==0)
            check("locally_acknowledged_removed",not outbox.exists())
            lines=ledger.read_text(encoding="utf-8").splitlines()
            check("HUB_ledger_one_signed_gap",len(lines)==1 and json.loads(lines[0])["evidence"]==signed)
            # Replay exact historical signed bytes: HUB must reject it.
            req=urllib.request.Request("http://127.0.0.1:8788/report",data=original,
                                       headers={"Content-Type":"application/json"},method="POST")
            try:
                urllib.request.urlopen(req,timeout=3)
                code=None
            except urllib.error.HTTPError as e:code=e.code
            check("HUB_replay_rejected",code==409)
            check("no_untrusted_public_feed",not list(root.rglob("feed*.json")))
        finally:
            hub.terminate()
            try:hub.wait(timeout=5)
            except subprocess.TimeoutExpired:hub.kill();hub.wait(timeout=3)
    return {"schema":"trapnet.signed-gap-e2e-lab.v046",
      "passed":all(x["passed"] for x in checks),
      "checks":len(checks),"network":"127.0.0.1-only",
      "HUB_public_listener":False,"real_Cowrie_modified":False,
      "production_modified":False,"lab_files_cleaned":True,
      "public_release_approved":False}

if __name__=="__main__":
    try:result=lab()
    except (OSError,ValueError,RuntimeError,AssertionError,subprocess.SubprocessError) as e:
        print(json.dumps({"schema":"trapnet.signed-gap-e2e-lab.v046",
            "passed":False,"error_class":type(e).__name__,
            "release_approved":False},sort_keys=True))
        sys.exit(3)
    print(json.dumps(result,sort_keys=True))
    sys.exit(0 if result["passed"] else 3)
