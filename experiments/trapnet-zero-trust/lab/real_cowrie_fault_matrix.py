#!/usr/bin/env python3
"""A2 disposable acceptance: genuine Cowrie JSON missing/torn/duplicate -> signed HUB.

Only an operator-triggered CI lab with immutable Cowrie image, non-networked
container, 16 MiB disposable ext4 and local HUB on 127.0.0.1:8788.
No real Cowrie deployment/logs, firewall actions, or public port changes.
"""
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

IMAGE_ID=ext4.IMAGE_DEFAULT

def invoke(argv,timeout=80):
    return subprocess.run(list(map(str,argv)),cwd=HERE,capture_output=True,
                          text=True,check=False,timeout=timeout)

def ready(proc):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(65):
        if proc.poll() is not None:return False
        try:
            with opener.open("http://127.0.0.1:8788/health",timeout=0.35) as r:
                if r.status==200:return True
        except (urllib.error.URLError,TimeoutError,OSError):
            time.sleep(0.11)
    return False

def exercise(image):
    if sys.platform!="linux" or os.geteuid()!=0:
        raise ValueError("root access on ephemeral Linux CI is required")
    if image!=IMAGE_ID:raise ValueError("wrong pinned Cowrie image")
    ext4.image_verified(image)
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1",8788))==0:
            raise RuntimeError("existing local HUB service; refuse test")
    checks={}
    counts={}
    def check(name,cond):
        checks[name]=bool(cond)
        if not cond:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="trapnet-real-cowrie-a2-") as td:
        parent=Path(td);parent.chmod(0o700)
        binDir=parent/"bin";binDir.mkdir(mode=0o700)
        for name in ("keygen","sensor","hub"):
            check("build_"+name,invoke(["go","build","-trimpath","-o",binDir/name,
                                       "./cmd/"+name],timeout=100).returncode==0)
        def fault(root,var,report):
            check("actual_cowrie_events_exist",report.get("second_events",0)>0)
            signer=root/"sensor-signer"
            check("ephemeral_signer",invoke([binDir/"keygen","-out",signer]).returncode==0)
            info=json.loads((signer/"node.json").read_text(encoding="utf-8"))
            allow=root/"allowlist.json"
            allow.write_text(json.dumps({info["node_id"]:info["public_key"]}),
                             encoding="utf-8")
            marker=root/bridge.MARKER
            marker.write_bytes(b"DISPOSABLE-ONLY\n")
            log=var/"log/cowrie/cowrie.json"
            baseline=log.read_bytes()
            check("genuine_cowrie_lines_are_valid",
                  len(baseline)>0 and baseline.endswith(b"\n") and
                  cowrie_log_health.assess(var)["passed"])
            lines=baseline.splitlines(keepends=True)
            check("genuine_events_available_for_duplicate",len(lines)>0)
            scenarios=[
                ("missing","log_unavailable",None),
                ("torn","log_corrupt",baseline+b'{"eventid":"cowrie.session.connect"'),
                ("duplicate","log_corrupt",baseline+lines[-1]),
                ("semantic_duplicate","log_corrupt",baseline+b" "+lines[-1]),
            ]
            pending=[]
            try:
                for name,expected,damaged in scenarios:
                    if damaged is None:log.unlink()
                    else:log.write_bytes(damaged)
                    health=cowrie_log_health.assess(var)
                    reason=cowrie_gap_advice.decide(health)
                    check(name+"_health_HOLD",not health["passed"] and reason["gap_reason"]==expected)
                    check(name+"_never_all_clear",reason["automatic_clear"] is False and
                          reason["observation_coverage_proven"] is False)
                    spool=root/("outbox-"+name);spool.mkdir(mode=0o700)
                    path=spool/"signed-gap.json"
                    dry=bridge.execute(root,var,path,signer/"private.hex",
                                       binDir/"sensor",emit=False)
                    check(name+"_default_no_network",
                          dry["status"]=="HOLD_MANUAL_SEND_NOT_ARMED" and not path.exists())
                    sent=bridge.execute(root,var,path,signer/"private.hex",
                                        binDir/"sensor",emit=True)
                    check(name+"_HUB_offline_preserves_signed_gap",
                          sent["status"]=="HOLD_PENDING_DELIVERY" and path.is_file())
                    raw=path.read_bytes()
                    signed=json.loads(raw)
                    check(name+"_immutable_private_gap",
                          signed["report"]["kind"]=="coverage_gap" and
                          signed["report"]["target_port"]==0 and len(raw)<8192)
                    pending.append((name,path,raw))
                    counts[name]=1
                    # Return the real log to its original bytes between cases.
                    log.write_bytes(baseline)
                healthy=cowrie_gap_advice.decide(cowrie_log_health.assess(var))
                check("repaired_log_does_not_prove_coverage",
                      healthy["status"]=="SNAPSHOT_PARSEABLE_COVERAGE_UNPROVEN" and
                      healthy["automatic_clear"] is False)
            finally:
                if not log.exists() or log.read_bytes()!=baseline:log.write_bytes(baseline)
            ledger=root/"signed-a2-ledger.jsonl"
            hubArgs=[binDir/"hub","-allowlist",allow,"-ledger",ledger]
            hub=subprocess.Popen(list(map(str,hubArgs)),cwd=HERE,stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                check("real_HUB_loopback_only_ready",ready(hub))
                for name,path,raw in pending:
                    response=invoke([binDir/"sensor","-key",signer/"private.hex",
                              "-gap-outbox",path,"-retry-gap-outbox"],timeout=20)
                    check(name+"_original_signature_delivered",response.returncode==0)
                    check(name+"_pending_removed_after_202",not path.exists())
                records=[json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
                check("real_HUB_ledger_contains_three_distinct_events",
                      len(records)==3 and
                      len({v["evidence"]["report"]["event_id"] for v in records})==3)
                hub.terminate();hub.wait(timeout=8)
                check("normal_HUB_stop_released_lock",not Path(str(ledger)+".lock").exists())
                hub=subprocess.Popen(list(map(str,hubArgs)),cwd=HERE,stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                check("HUB_restarted_from_three_durable_events",ready(hub))
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                for name,path,raw in pending:
                    req=urllib.request.Request("http://127.0.0.1:8788/report",
                       data=raw,headers={"Content-Type":"application/json"},method="POST")
                    try:
                        opener.open(req,timeout=3)
                        status=0
                    except urllib.error.HTTPError as err:
                        status=err.code
                    check(name+"_replay_rejected_after_restart",status==409)
                check("historic_faults_not_deleted",
                      len(ledger.read_text(encoding="utf-8").splitlines())==3)
            finally:
                if hub.poll() is None:
                    hub.terminate()
                    try:hub.wait(timeout=8)
                    except subprocess.TimeoutExpired:hub.kill();hub.wait(timeout=3)
            return True
        outcome=ext4.trial(image,storage_parent=str(parent),fault_hook=fault)
        if not outcome["passed"] or not outcome.get("cleanup"):
            return {"schema":"trapnet.real-cowrie-a2-fault-matrix.v050",
                    "passed":False,"failure_stage":outcome.get("failure_stage","UNKNOWN"),
                    "error_class":outcome.get("error_class","UNKNOWN"),
                    "lab_cleanup":outcome.get("cleanup",False),
                    "production_modified":False,"release_approved":False}
    return {"schema":"trapnet.real-cowrie-a2-fault-matrix.v050",
            "passed":all(checks.values()),"checks_passed":len(checks),
            "faults_tested":sorted(counts),"real_cowrie_events_observed":True,
            "separate_disposable_ext4":True,
            "real_Sensor_HUB_used":True,
            "hub_loopback_only":True,"cowrie_network_disabled":True,
            "lab_cleanup":True,"raw_events_exported":False,
            "signer_keys_exported":False,"production_modified":False,
            "release_approved":False}

def main():
    if len(sys.argv)!=2 or sys.argv[1]!=IMAGE_ID:
        print('{"passed":false,"error_class":"UNPINNED_IMAGE"}')
        return 3
    try:r=exercise(sys.argv[1])
    except (AssertionError,RuntimeError,ValueError,OSError,subprocess.SubprocessError) as e:
        label=str(e)
        if not (isinstance(e,AssertionError) and len(label)<90
                and label.replace("_","").isalnum()):label="HOLD"
        r={"schema":"trapnet.real-cowrie-a2-fault-matrix.v050",
            "passed":False,"error_class":type(e).__name__,
            "failure_check":label,"release_approved":False}
    print(json.dumps(r,sort_keys=True))
    return 0 if r["passed"] else 3

if __name__=="__main__":
    sys.exit(main())
