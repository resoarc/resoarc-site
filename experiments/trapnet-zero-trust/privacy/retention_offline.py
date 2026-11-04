#!/usr/bin/env python3
"""Fail-closed, OFFLINE-only rehearsal of TrapNet raw-log retention.

This is deliberately not deployable against live Cowrie: it requires a
private, synthetic-only, explicitly named staging directory and a sentinel.
No networking, no recursive traversal, no production paths, no scheduled
deletion. Dry-run by default; apply needs a matching previously printed
SHA256 of the exact plan. This does not establish legal retention compliance.
"""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys
from datetime import datetime, timezone

STAGE="trapnet-retention-offline-"
SENTINEL=".trapnet-retention-offline.json"
VERSION="trapnet.offline-log-retention.v060"
LOG_RE=re.compile(r"cowrie-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{16}\.jsonl\Z")
MAX_ITEMS=5000
MAX_FILE_BYTES=64*1024*1024

def require_stage(root):
    root=Path(root)
    if not root.is_absolute() or not root.name.startswith(STAGE) or root.resolve()!=root:
        raise ValueError("requires exact absolute, non-symlink synthetic staging root")
    sb=os.lstat(root)
    if not stat.S_ISDIR(sb.st_mode) or sb.st_uid!=os.geteuid() or (sb.st_mode & 0o077):
        raise ValueError("staging root must be owned and 0700")
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
    fd=os.open(root,flags)
    return fd

def stat_safe(fd,name):
    st=os.stat(name,dir_fd=fd,follow_symlinks=False)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.geteuid():
        raise ValueError("refusing non-regular, hardlinked or foreign-owned entry")
    if st.st_mode & 0o077 or st.st_size>MAX_FILE_BYTES:
        raise ValueError("file permissions or size not accepted")
    return st

def make_plan(root,cutoff):
    root=Path(root)
    fd=require_stage(root)
    try:
        marker=stat_safe(fd,SENTINEL)
        if marker.st_size>1024:
            raise ValueError("invalid staging sentinel")
        with os.fdopen(os.open(SENTINEL,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd),"rb") as f:
            payload=json.load(f)
        if payload!={"schema":VERSION,"synthetic_only":True}:
            raise ValueError("not a synthetic-only staging directory")
        names=sorted(os.listdir(fd))
        if len(names)>MAX_ITEMS+1:
            raise ValueError("too many candidate entries")
        entries=[]
        for name in names:
            if name==SENTINEL:
                continue
            if not LOG_RE.fullmatch(name):
                raise ValueError("unexpected entry in offline retention stage")
            st=stat_safe(fd,name)
            record={"name":name,"ino":st.st_ino,"dev":st.st_dev,
                    "size":st.st_size,"mtime_ns":st.st_mtime_ns,
                    "ctime_ns":st.st_ctime_ns}
            entries.append((record,st))
        if not entries:
            raise ValueError("empty staging evidence; no plan to approve")
        old=[record for record,st in entries if st.st_mtime_ns<cutoff]
        recent=[record for record,st in entries if st.st_mtime_ns>=cutoff]
        dir_stat=os.fstat(fd)
        basis={"schema":VERSION,"dir_dev":dir_stat.st_dev,
               "dir_inode":dir_stat.st_ino,"cutoff_ns":cutoff,
               "files":[record for record,_ in entries]}
        digest=hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()
        return digest,old,recent
    finally:
        os.close(fd)

def action(root,cutoff,approved=None):
    plan,old,recent=make_plan(root,cutoff)
    if approved is None:
        return {"schema":VERSION,"status":"DRY_RUN","passed":True,
                "candidate_old":len(old),"preserved_recent":len(recent),
                "plan_sha256":plan,"deleted":0,"production_modified":False}
    if not re.fullmatch(r"[0-9a-f]{64}",approved) or not hmac.compare_digest(plan,approved):
        raise ValueError("approved manifest mismatches current staging snapshot")
    # Re-check plan just before apply. A malicious race by the *same owner*
    # cannot be defeated without pausing the source: this is offline only.
    fd=require_stage(root)
    removed=0
    try:
        for record in old:
            st=stat_safe(fd,record["name"])
            for attr,key in (("st_ino","ino"),("st_dev","dev"),("st_size","size"),
                             ("st_mtime_ns","mtime_ns"),("st_ctime_ns","ctime_ns")):
                if getattr(st,attr)!=record[key]:
                    raise ValueError("stale approval: file changed before deletion")
            os.unlink(record["name"],dir_fd=fd)
            removed+=1
    finally:
        os.close(fd)
    return {"schema":VERSION,"status":"APPLIED_TO_SYNTHETIC_STAGE",
            "passed":True,"candidate_old":len(old),"preserved_recent":len(recent),
            "plan_sha256":plan,"deleted":removed,"production_modified":False}

def parse_cutoff(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",value):
        raise ValueError("UTC timestamp YYYY-MM-DDTHH:MM:SSZ required")
    moment=datetime.strptime(value,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(moment.timestamp()*1_000_000_000)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--cutoff-utc",required=True)
    p.add_argument("--apply-with-approved-plan",default=None)
    args=p.parse_args()
    try:
        result=action(args.root,parse_cutoff(args.cutoff_utc),args.apply_with_approved_plan)
    except (ValueError,OSError,TypeError,json.JSONDecodeError) as exc:
        result={"schema":VERSION,"passed":False,"status":"HOLD",
                "error_class":type(exc).__name__,"production_modified":False}
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 3

if __name__=="__main__":
    sys.exit(main())
