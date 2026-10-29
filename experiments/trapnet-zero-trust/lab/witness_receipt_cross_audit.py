#!/usr/bin/env python3
"""Offline, disposable integration of real signed Sensor/HUB receipt and Witness.

All private files and signer keys are temporary, local-only, separate test dirs.
This does not establish two independent operators or independent key custody.
"""
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
HUB="http://127.0.0.1:8788"

def run(argv, timeout=90):
    return subprocess.run([str(x) for x in argv],cwd=ROOT,capture_output=True,
                          text=True,timeout=timeout,check=False)

def ready(proc):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(60):
        if proc.poll() is not None:return False
        try:
            with opener.open(HUB+"/health",timeout=0.3) as r:
                if r.status==200:return True
        except (urllib.error.URLError,TimeoutError,OSError):
            time.sleep(0.1)
    return False

def lab():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1",8788))==0:
            raise RuntimeError("refuse preexisting HUB service")
    checks={}
    def check(name,good):
        checks[name]=bool(good)
        if not good:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="trapnet-witness-receipt-audit-") as td:
        base=Path(td);base.chmod(0o700)
        bin=base/"bin";bin.mkdir(mode=0o700)
        for exe in ("keygen","sensor","hub","snapshot","witness","receipt-audit"):
            check("build_"+exe,run(["go","build","-trimpath","-o",bin/exe,"./cmd/"+exe]).returncode==0)
        for role in ("sensor","hub","independent-witness"):
            check("ephemeral_key_"+role,
                  run([bin/"keygen","-out",base/role]).returncode==0)
        info=json.loads((base/"sensor"/"node.json").read_text(encoding="utf-8"))
        allow=base/"allowlist.json"
        allow.write_text(json.dumps({info["node_id"]:info["public_key"]}),encoding="utf-8")
        spool=base/"sensor-spool";spool.mkdir(mode=0o700)
        pending=spool/"pending.json"
        sensor_args=[bin/"sensor","-key",base/"sensor"/"private.hex",
            "-gap-outbox",pending,"-hub-receipt-pub",base/"hub"/"public.hex"]
        result=run([*sensor_args,"-gap-reason","storage_full"],timeout=15)
        check("offline_signed_gap_pending",result.returncode!=0 and pending.is_file())
        original=pending.read_bytes()
        report=base/"signed-report.json";report.write_bytes(original)
        ledger=base/"private-hub"/"ledger.jsonl"
        ledger.parent.mkdir(mode=0o700)
        hub_args=[bin/"hub","-allowlist",allow,"-ledger",ledger,
                  "-receipt-key",base/"hub"/"private.hex"]
        hub=subprocess.Popen([str(v) for v in hub_args],cwd=ROOT,
              stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            check("HUB_loopback_ready",ready(hub))
            req=urllib.request.Request(HUB+"/report",data=original,method="POST",
                 headers={"Content-Type":"application/json"})
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=5) as response:
                code=response.status
                ack=response.read(2049)
            check("signed_202_from_real_HUB",code==202 and b'"signature"' in ack)
            receiptFile=base/"signed-hub-receipt.json"
            receiptFile.write_bytes(ack)
            check("lost_ACK_leaves_pending",pending.exists())
        finally:
            if hub.poll() is None:
                hub.terminate()
                try:hub.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    hub.kill();hub.wait(timeout=3)
        check("HUB_stopped_without_stale_lock",not Path(str(ledger)+".lock").exists())
        snapParent=base/"offhub-snapshot";snapParent.mkdir(mode=0o700)
        snap=snapParent/"snapshot-1"
        check("closed_ledger_snapshot",run([bin/"snapshot","-ledger",ledger,"-out",snap]).returncode==0)
        snapshotLedger=snap/"ledger.jsonl"
        independent=base/"independent-history";independent.mkdir(mode=0o700)
        history=independent/"history.jsonl"
        attest=run([bin/"witness","-mode","attest","-ledger",snapshotLedger,
                "-history",history,"-key",base/"independent-witness"/"private.hex",
                "-bootstrap-history"])
        match=re.search(r"\btip=([0-9a-f]{64})\b",attest.stdout)
        check("independent_Witness_signs_snapshot",attest.returncode==0 and match is not None)
        tip=match.group(1)
        auditArgs=[bin/"receipt-audit","-ledger",snapshotLedger,"-history",history,
          "-witness-tip",tip,
          "-witness-pub",base/"independent-witness"/"public.hex",
          "-hub-pub",base/"hub"/"public.hex",
          "-sensor-pub",base/"sensor"/"public.hex",
          "-report",report,"-receipt",receiptFile]
        audit=run(auditArgs)
        check("three_key_offline_cross_audit",audit.returncode==0 and
              "RECEIPT_WITNESS_AUDIT_PASS" in audit.stdout)
        check("independent_audit_does_not_clear_pending",pending.is_file())
        check("reject_wrong_independent_tip",
              run([*auditArgs[:6],"0"*64,*auditArgs[7:]]).returncode!=0)
        forged=json.loads(ack)
        forged["receipt"]["ledger_rows"]+=1
        receiptFile.write_text(json.dumps(forged),encoding="utf-8")
        check("reject_modified_HUB_receipt",run(auditArgs).returncode!=0)
        receiptFile.write_bytes(ack)
        headFile=Path(str(snapshotLedger)+".head")
        originalHead=headFile.read_bytes()
        headFile.write_text("{}",encoding="utf-8")
        check("reject_tampered_snapshot_checkpoint",run(auditArgs).returncode!=0)
        headFile.write_bytes(originalHead)
        historyBytes=history.read_bytes()
        history.write_bytes(historyBytes[:-8]+b"altered\n")
        check("reject_modified_Witness_history",run(auditArgs).returncode!=0)
        history.write_bytes(historyBytes)
        check("restore_audit_after_negative_tests",run(auditArgs).returncode==0)
        check("pending_kept_for_HUB_authenticated_retry",pending.is_file())
    return {"schema":"trapnet.witness-receipt-cross-audit.v049",
      "passed":all(checks.values()),"checks_passed":len(checks),
      "real_cli_and_offline_Witness_used":True,
      "witness_key_separate_from_HUB_key":True,
      "actual_independent_operator_attestation":False,
      "HUB_network":"127.0.0.1-only",
      "raw_events_exported":False,"private_keys_exported":False,
      "test_files_cleaned":True,"production_modified":False,
      "public_release_approved":False}

def main():
    try:r=lab()
    except (AssertionError,OSError,ValueError,RuntimeError,subprocess.SubprocessError) as e:
        r={"schema":"trapnet.witness-receipt-cross-audit.v049","passed":False,
        "failure":str(e) if isinstance(e,AssertionError) and str(e).replace("_","").isalnum() and len(str(e))<80 else "HOLD",
        "error_class":type(e).__name__,"public_release_approved":False}
    print(json.dumps(r,sort_keys=True))
    return 0 if r["passed"] else 3

if __name__=="__main__":sys.exit(main())
