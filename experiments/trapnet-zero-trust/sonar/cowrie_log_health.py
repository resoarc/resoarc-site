#!/usr/bin/env python3
"""Read-only Cowrie JSON log + bounded storage preflight.

Avoid raw log, network, shell and mutation. Deliberately fails closed when
the backing filesystem's capacity/quota cannot be shown to be bounded.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import sys

MAX_LINE=65536
DEFAULT_CEILING=16*1024*1024
DEFAULT_MIN_FREE=2*1024*1024
DEFAULT_MAX_LOG=2*1024*1024

def assess(root,capacity_ceiling=DEFAULT_CEILING,min_free=DEFAULT_MIN_FREE,max_log=DEFAULT_MAX_LOG):
    issues=[]
    def fail(reason):
        if reason not in issues:issues.append(reason)
    root=Path(root)
    result={"schema":"trapnet.cowrie-log-health.v1","passed":False,
            "source":"untrusted_private_log_data","public_beta_ready":False,
            "disk_full_simulation":False,"new_event_append_proven":False,
            "log_entries":0,"capacity_bytes":None,"free_bytes":None,
            "issues":issues,"sensitive_log_content_exported":False}
    if (type(capacity_ceiling) is not int or type(min_free) is not int or
        type(max_log) is not int or not 0<min_free<capacity_ceiling<=512*1024*1024 or
        not 0<max_log<=capacity_ceiling):
        fail("INVALID_THRESHOLDS");return result
    try:
        if root.is_symlink() or not root.is_dir():
            fail("VAR_ROOT_UNSAFE");return result
        for relative in ("log","log/cowrie","log/cowrie/cowrie.json"):
            item=root/relative
            if item.is_symlink():fail("LOG_PATH_SYMLINK");return result
        space=os.statvfs(root)
        capacity=space.f_blocks*space.f_frsize
        free=space.f_bavail*space.f_frsize
        result["capacity_bytes"]=capacity
        result["free_bytes"]=free
        if capacity<=0 or capacity>capacity_ceiling:fail("VOLUME_LIMIT_NOT_PROVEN")
        if free<min_free:fail("FREE_SPACE_LOW")
        log=root/"log/cowrie/cowrie.json"
        if not log.exists():fail("JSON_LOG_MISSING");return result
        st=log.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:
            fail("JSON_LOG_TYPE_UNSAFE");return result
        if st.st_size<=0:fail("JSON_LOG_EMPTY");return result
        if st.st_size>max_log:fail("JSON_LOG_TOO_LARGE");return result
        with log.open("rb") as f:
            while True:
                line=f.readline(MAX_LINE+2)
                if not line:break
                if len(line)>MAX_LINE or not line.endswith(b"\n"):
                    fail("JSON_LINE_INVALID");break
                try:item=json.loads(line)
                except (ValueError,UnicodeError):
                    fail("JSON_LINE_INVALID");break
                if not isinstance(item,dict) or type(item.get("eventid")) is not str:
                    fail("JSON_EVENT_INVALID");break
                result["log_entries"]+=1
        if result["log_entries"]<=0:fail("JSON_LOG_NO_EVENTS")
    except (OSError,ValueError,TypeError):
        fail("IO_OR_FORMAT_ERROR")
    result["passed"]=not issues
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--private-var",required=True)
    parser.add_argument("--capacity-ceiling-bytes",type=int,default=DEFAULT_CEILING)
    parser.add_argument("--min-free-bytes",type=int,default=DEFAULT_MIN_FREE)
    parser.add_argument("--max-log-bytes",type=int,default=DEFAULT_MAX_LOG)
    a=parser.parse_args()
    result=assess(a.private_var,a.capacity_ceiling_bytes,a.min_free_bytes,a.max_log_bytes)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 3

if __name__=="__main__":sys.exit(main())
