#!/usr/bin/env python3
"""Real isolated Cowrie/ext4 -> signed Sensor outbox -> actual loopback HUB v0.47.

CI-only root execution, ephemeral storage and identities. This uses Cowrie's
actual SSH-triggered JSON output on an ext4 loop filesystem (not test JSON).
The injected ENOSPC pressure is confined to that 16 MiB disposable filesystem.
The ONLY receiver is 127.0.0.1:8788; no Docker public ports or network.
"""
import argparse
import hashlib
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
import cowrie_ext4_persistent_rehearsal as ext4
import cowrie_log_health
import cowrie_gap_advice
import cowrie_gap_lab_bridge as bridge

PORT=8788
IMAGE_ID=ext4.IMAGE_DEFAULT
IMAGE_REF="cowrie/cowrie@sha256:69e3317c6ecf8811d18faecb8a2fcedee0af1f0f864b50de07b688c7409f515c"

def invoke(argv,timeout=30):
    return subprocess.run(list(map(str,argv)),cwd=HERE,capture_output=True,text=True,
                          timeout=timeout,check=False)

def wait_hub(proc):
    # Never confuse a stale background HUB with the process we launched.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(45):
        if proc.poll() is not None:return False
        try:
            with opener.open("http://127.0.0.1:8788/health",timeout=0.4) as response:
                if response.status==200:return True
        except (urllib.error.URLError,TimeoutError,OSError):time.sleep(0.12)
    return False

def exercise(image):
    if not sys.platform.startswith("linux") or os.geteuid()!=0:
        raise ValueError("root Linux isolated CI required")
    if image!=IMAGE_ID:raise ValueError("unrecognized immutable Cowrie image")
    ext4.image_verified(image)
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1",PORT))==0:
            raise RuntimeError("refuse to test with existing HUB listener")

    checks={}
    state={}
    def check(name,condition):
        checks[name]=bool(condition)
        if not condition:raise AssertionError(name)

    with tempfile.TemporaryDirectory(prefix="trapnet-real-cowrie-gap-v047-") as temp:
        parent=Path(temp)
        parent.chmod(0o700)
        bindir=parent/"bin";bindir.mkdir(mode=0o700)
        for binary in ("keygen","sensor","hub"):
            check("built_"+binary,invoke(["go","build","-trimpath","-o",bindir/binary,
                                          "./cmd/"+binary],timeout=100).returncode==0)

        def at_full(root,var,report):
            check("actual_cowrie_generated_events",report.get("first_events",0)>0)
            # This marker makes the operator gate refuse the production tree
            # and permits only one disposable, explicitly selected trial.
            (root/bridge.MARKER).write_bytes(b"DISPOSABLE-ONLY\n")
            keydir=root/"ephemeral-signer"
            check("test_identity_generated",
                  invoke([bindir/"keygen","-out",keydir]).returncode==0)
            node=json.loads((keydir/"node.json").read_text(encoding="utf-8"))
            allow=root/"allowlist.json"
            allow.write_text(json.dumps({node["node_id"]:node["public_key"]}),
                             encoding="utf-8")
            spool=root/"outbox";spool.mkdir(mode=0o700)
            pending=spool/"coverage-gap.json"
            key=keydir/"private.hex"
            dry=bridge.execute(root,var,pending,key,bindir/"sensor",emit=False)
            check("real_full_ext4_classified_storage_gap",
                  dry["gap_reason"]=="storage_full" and
                  dry["status"]=="HOLD_MANUAL_SEND_NOT_ARMED")
            sent=bridge.execute(root,var,pending,key,bindir/"sensor",emit=True)
            check("offline_hub_keeps_signed_gap",
                  sent["status"]=="HOLD_PENDING_DELIVERY" and pending.is_file())
            data=pending.read_bytes()
            signed=json.loads(data)
            check("persisted_gap_is_non_attack",
                  signed["report"]["kind"]=="coverage_gap" and
                  signed["report"]["target_port"]==0 and len(data)<8192)
            state.update({"node":node,"allow":allow,"pending":pending,"key":key,
                          "signed":signed,"digest":hashlib.sha256(data).hexdigest(),
                          "source_log_count":report["first_events"]})
            return True

        def after_recover(root,var,report):
            recovered=cowrie_gap_advice.decide(cowrie_log_health.assess(var))
            check("recovered_real_log_parseable_without_auto_clear",
                  recovered["status"]=="SNAPSHOT_PARSEABLE_COVERAGE_UNPROVEN" and
                  recovered["automatic_clear"] is False)
            pending=state["pending"]
            check("pending_gap_survives_cowrie_state_recovery",pending.is_file())
            original=pending.read_bytes()
            check("signed_gap_bytes_stable",hashlib.sha256(original).hexdigest()==state["digest"])
            ledger=root/"signed-hub-ledger.jsonl"
            hub_args=[bindir/"hub","-allowlist",state["allow"],"-ledger",ledger]
            hub=subprocess.Popen(list(map(str,hub_args)),cwd=HERE,stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                check("real_loopback_hub_started",wait_hub(hub))
                resend=invoke([bindir/"sensor","-key",state["key"],
                               "-gap-outbox",pending,"-retry-gap-outbox"],timeout=20)
                check("signed_gap_retried_same_event",resend.returncode==0)
                check("hub_202_clears_outbox",not pending.exists())
                rows=ledger.read_text(encoding="utf-8").splitlines()
                check("hub_durably_records_original_gap",
                      len(rows)==1 and json.loads(rows[0])["evidence"]==state["signed"])
                hub.terminate()
                hub.wait(timeout=7)
                check("graceful_hub_stop_releases_ledger_lock",
                      not Path(str(ledger)+".lock").exists())
                hub=subprocess.Popen(list(map(str,hub_args)),cwd=HERE,
                                     stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                check("hub_restart_from_persistent_ledger",wait_hub(hub))
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                req=urllib.request.Request("http://127.0.0.1:8788/report",
                    data=original,headers={"Content-Type":"application/json"},method="POST")
                try:
                    opener.open(req,timeout=4)
                    result=None
                except urllib.error.HTTPError as err:result=err.code
                check("replay_rejected_after_restart",result==409)
                check("historical_gap_not_automatically_erased",
                      len(ledger.read_text(encoding="utf-8").splitlines())==1)
            finally:
                if hub.poll() is None:
                    hub.terminate()
                    try:hub.wait(timeout=7)
                    except subprocess.TimeoutExpired:
                        hub.kill();hub.wait(timeout=4)
            return True

        result=ext4.trial(image,storage_parent=str(parent),
                          failure_hook=at_full,recovery_hook=after_recover)
        if not result.get("passed") or not result.get("cleanup"):
            return {"schema":"trapnet.real-cowrie-signed-gap-e2e.v047",
                    "passed":False,"failure_stage":result.get("failure_stage","unknown"),
                    "error_class":result.get("error_class","unknown"),
                    "cleanup":result.get("cleanup",False),"checks":checks,
                    "production_modified":False,"release_approved":False}
    return {"schema":"trapnet.real-cowrie-signed-gap-e2e.v047","passed":all(checks.values()),
        "checks_passed":len(checks),"ext4_capacity_target":ext4.CAPACITY,
        "real_cowrie_events_observed":state.get("source_log_count",0),
        "actual_container_used":True,"no_public_ports":True,"cowrie_network":"none",
        "hub_network":"127.0.0.1-only","cleanup":True,"production_modified":False,
        "raw_events_exported":False,"private_keys_exported":False,"release_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--image-id",required=True)
    args=p.parse_args()
    try:
        result=exercise(args.image_id)
    except (OSError,ValueError,RuntimeError,AssertionError,
            subprocess.SubprocessError) as err:
        result={"schema":"trapnet.real-cowrie-signed-gap-e2e.v047","passed":False,
                "error_class":type(err).__name__,
                "failed_check":str(err) if isinstance(err,AssertionError) and
                    len(str(err))<90 and str(err).replace("_","").isalnum() else "not_disclosed",
                "release_approved":False}
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 3

if __name__=="__main__":sys.exit(main())
