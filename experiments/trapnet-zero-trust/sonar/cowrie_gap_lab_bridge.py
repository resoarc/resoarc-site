#!/usr/bin/env python3
"""TrapNet experimental Cowrie -> signed gap bridge.

Operator-triggered, LAB ONLY. A direct Cowrie-health finding is classified
before invoking the existing Sensor once. On failure its signed notification
remains in the private durable outbox. No watcher, cron, release, remote
listener, log content export or automatic all-clear.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import cowrie_log_health
import cowrie_gap_advice

MARKER=".trapnet-disposable-gap-lab-v046"
SCHEMA="trapnet.cowrie-signed-gap-lab-bridge.v046"

def secure_lab(lab_root,private_var,outbox,key,sensor):
    root=Path(lab_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError("unsafe lab root")
    root=root.resolve(strict=True)
    if root == Path("/") or len(root.parts)<3 or (os.name=="posix" and root.stat().st_mode & 0o077):
        raise ValueError("lab root must be a private disposable directory")
    marker=root/MARKER
    if marker.is_symlink() or not marker.is_file() or marker.read_bytes()!=b"DISPOSABLE-ONLY\n":
        raise ValueError("lab authorization marker missing")
    def contained(path,kind):
        value=Path(path)
        if not value.is_absolute() or value.is_symlink():
            raise ValueError("unsafe "+kind)
        resolved=value.resolve(strict=False)
        if resolved==root or root not in resolved.parents:
            raise ValueError("path escapes disposable lab: "+kind)
        return value
    private_var=contained(private_var,"private var")
    outbox=contained(outbox,"outbox")
    key=contained(key,"test signer")
    if not private_var.is_dir() or private_var.is_symlink():
        raise ValueError("private var directory missing")
    if not key.is_file() or key.is_symlink() or (os.name=="posix" and key.stat().st_mode&0o077):
        raise ValueError("test signer must be a private regular file")
    spool_parent=outbox.parent
    if spool_parent.is_symlink() or not spool_parent.is_dir() or (os.name=="posix" and spool_parent.stat().st_mode&0o077):
        raise ValueError("unsafe pending spool parent")
    if outbox.exists() or outbox.is_symlink() or Path(str(outbox)+".lock").exists():
        raise ValueError("unresolved signed notice or stale lock: manual recovery required")
    if not Path(sensor).is_absolute() or Path(sensor).is_symlink() or not Path(sensor).is_file():
        raise ValueError("missing pinned local test Sensor binary")
    return private_var,outbox,key,Path(sensor)

def execute(lab_root,private_var,outbox,key,sensor,emit=False,runner=subprocess.run):
    result={"schema":SCHEMA,"status":"HOLD","operator_action_required":True,
        "notification_sent":False,"release_approved":False,
        "automatic_healthy_assessment":False,"raw_log_exported":False}
    try:
        private_var,outbox,key,sensor=secure_lab(lab_root,private_var,outbox,key,sensor)
        health=cowrie_log_health.assess(private_var)
        advice=cowrie_gap_advice.decide(health)
        result["health_passed"]=health.get("passed") is True
        result["advice_status"]=advice["status"]
        result["gap_reason"]=advice["gap_reason"]
        if not advice["gap_notice_recommended"]:
            result["status"]="HOLD_NO_VERIFIED_GAP_REASON"
            return result
        if not emit:
            result["status"]="HOLD_MANUAL_SEND_NOT_ARMED"
            return result
        command=[str(sensor),"-key",str(key),"-gap-reason",advice["gap_reason"],
                 "-gap-outbox",str(outbox)]
        # Never print or record CLI output: it may contain diagnostic details.
        delivered=runner(command,capture_output=True,text=True,timeout=12,check=False)
        result["status"]="LAB_202_ACK_RECEIVED" if delivered.returncode==0 else "HOLD_PENDING_DELIVERY"
        result["notification_sent"]=delivered.returncode==0
        result["pending_file_present"]=outbox.exists()
        if delivered.returncode==0 and outbox.exists():
            result["status"]="HOLD_INCONSISTENT_ACK_AND_PENDING"
            result["notification_sent"]=False
    except (OSError,ValueError,subprocess.SubprocessError):
        result["status"]="HOLD_LAB_PRECONDITION_OR_IO_FAILURE"
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--lab-root",required=True)
    p.add_argument("--private-var",required=True)
    p.add_argument("--outbox",required=True)
    p.add_argument("--key",required=True)
    p.add_argument("--sensor",required=True)
    p.add_argument("--emit",action="store_true",help="explicit one-shot test Sensor send; default is no send")
    a=p.parse_args()
    result=execute(a.lab_root,a.private_var,a.outbox,a.key,a.sensor,emit=a.emit)
    print(json.dumps(result,sort_keys=True))
    # This is never release success; a 202 ACK is only a lab delivery proof.
    return 0 if result["status"] in ("LAB_202_ACK_RECEIVED","HOLD_MANUAL_SEND_NOT_ARMED") else 3

if __name__=="__main__":
    sys.exit(main())
