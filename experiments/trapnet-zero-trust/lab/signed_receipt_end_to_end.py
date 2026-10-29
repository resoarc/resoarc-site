#!/usr/bin/env python3
"""Disposable localhost-only signed HUB 202/409 receipt acceptance v0.48.

Compiles actual Go HUB/Sensor/keygen, tests a lost HTTP 202 and a signed 409
after HUB restart. Private keys, signed report contents and raw HTTP bodies
stay within the temporary directory. No production services or open ports.
"""
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
URL="http://127.0.0.1:8788"

def call(argv,timeout=90):
    return subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,
                          check=False,timeout=timeout)

def ready(proc):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(55):
        if proc.poll() is not None:return False
        try:
            with opener.open(URL+"/health",timeout=0.4) as response:
                if response.status==200:return True
        except (urllib.error.URLError,TimeoutError,OSError):time.sleep(0.1)
    return False

def run():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1",8788))==0:
            raise RuntimeError("HUB loopback port occupied; refuse existing services")
    checks={}
    def check(name,condition):
        checks[name]=bool(condition)
        if not condition:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="trapnet-signed-ack-e2e-") as td:
        base=Path(td);base.chmod(0o700)
        bins=base/"bin";bins.mkdir(mode=0o700)
        for exe in ("keygen","sensor","hub"):
            check("build_"+exe,call(["go","build","-trimpath","-o",bins/exe,"./cmd/"+exe]).returncode==0)
        for identity in ("sensor","hub","untrusted"):
            check("create_"+identity,call([bins/"keygen","-out",base/identity]).returncode==0)
        node=json.loads((base/"sensor"/"node.json").read_text(encoding="utf-8"))
        allow=base/"allowlist.json"
        allow.write_text(json.dumps({node["node_id"]:node["public_key"]}),encoding="utf-8")
        spool=base/"spool";spool.mkdir(mode=0o700)
        pending=spool/"pending.json"
        sensor_base=[bins/"sensor","-key",base/"sensor"/"private.hex",
            "-gap-outbox",pending,"-hub-receipt-pub",base/"hub"/"public.hex"]
        first=call([*sensor_base,"-gap-reason","storage_full"],timeout=20)
        check("offline_sensor_preserves_signed_gap",first.returncode!=0 and pending.is_file())
        original=pending.read_bytes()
        parsed=json.loads(original)
        check("only_signed_gap_in_outbox",parsed["report"]["kind"]=="coverage_gap")
        ledger=base/"hub-ledger.jsonl"
        hub_args=[bins/"hub","-allowlist",allow,"-ledger",ledger,
                  "-receipt-key",base/"hub"/"private.hex"]
        hub=subprocess.Popen(list(map(str,hub_args)),cwd=ROOT,stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            check("signed_receipt_hub_ready",ready(hub))
            req=urllib.request.Request(URL+"/report",data=original,
                headers={"Content-Type":"application/json"},method="POST")
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req,timeout=5) as response:
                code=response.status
                body=response.read(2049)
            check("HUB_accepts_and_signs_202",code==202 and
                  b'"signature":' in body and b'"report_sha256":' in body)
            check("lost_ack_keeps_outbox",pending.is_file())
            hub.terminate()
            hub.wait(timeout=7)
            check("HUB_release_lock_on_graceful_stop",
                  not Path(str(ledger)+".lock").exists())
            hub=subprocess.Popen(list(map(str,hub_args)),cwd=ROOT,stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            check("HUB_restart_from_existing_ledger",ready(hub))
            recovered=call([*sensor_base,"-retry-gap-outbox"],timeout=20)
            check("signed_409_resolves_exact_original",recovered.returncode==0)
            check("pending_removed_only_after_verified_receipt",not pending.exists())
            check("exactly_one_signed_ledger_row",len(ledger.read_text(encoding="utf-8").splitlines())==1)
            # The wrong pinned public key MUST reject even a correctly signed
            # new HUB 202; no false proof of successful delivery.
            wrong=call([bins/"sensor","-key",base/"sensor"/"private.hex",
                        "-gap-outbox",pending,"-hub-receipt-pub",base/"untrusted"/"public.hex",
                        "-gap-reason","log_corrupt"],timeout=20)
            check("untrusted_HUB_key_refuses_202",wrong.returncode!=0 and pending.is_file())
            rows=ledger.read_text(encoding="utf-8").splitlines()
            check("untrusted_pin_never_truncates_ledger",len(rows)==2)
        finally:
            if hub.poll() is None:
                hub.terminate()
                try:hub.wait(timeout=7)
                except subprocess.TimeoutExpired:hub.kill();hub.wait(timeout=5)
    return {"schema":"trapnet.signed-hub-receipt-e2e.v048",
        "passed":all(checks.values()),"checks_passed":len(checks),
        "hub_network":"127.0.0.1-only",
        "signed_202_and_409_proven":True,"forged_public_key_rejected":True,
        "raw_ledger_exported":False,"ephemeral_signers_cleaned":True,
        "production_modified":False,"public_release_approved":False}

def main():
    try:
        result=run()
    except (OSError,ValueError,AssertionError,RuntimeError,
            subprocess.SubprocessError) as exc:
        safe=str(exc) if isinstance(exc,AssertionError) and str(exc).replace("_","").isalnum() and len(str(exc))<100 else "HOLD"
        result={"schema":"trapnet.signed-hub-receipt-e2e.v048",
             "passed":False,"error_class":type(exc).__name__,
             "failed_check":safe,"public_release_approved":False}
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 3

if __name__=="__main__":sys.exit(main())
