#!/usr/bin/env python3
"""Read-only Cowrie JSON log + bounded storage preflight (Linux).

The report is deliberately not a release approval, liveness proof, or event
completeness guarantee. Open each directory/file by pinned descriptor, reject
symlinks and hardlinks, and verify the *actual log file* storage capacity.
Neither raw events nor filesystem paths are printed.
"""
import argparse
from contextlib import ExitStack
import json
import hashlib
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
    # Fail closed on platforms that cannot pin a symlink-free descriptor chain.
    if not getattr(os,"O_NOFOLLOW",0) or not getattr(os,"O_DIRECTORY",0) or not hasattr(os,"fstatvfs"):
        fail("PINNED_FILE_OPEN_UNAVAILABLE");return result
    try:
        if root.is_symlink() or not root.is_dir():
            fail("VAR_ROOT_UNSAFE");return result
        for relative in ("log","log/cowrie","log/cowrie/cowrie.json"):
            if (root/relative).is_symlink():
                fail("LOG_PATH_SYMLINK");return result
        directory_flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|getattr(os,"O_CLOEXEC",0)
        file_flags=os.O_RDONLY|os.O_NOFOLLOW|getattr(os,"O_NONBLOCK",0)|getattr(os,"O_CLOEXEC",0)
        with ExitStack() as stack:
            rootfd=os.open(str(root),directory_flags)
            stack.callback(os.close,rootfd)
            logfd=os.open("log",directory_flags,dir_fd=rootfd)
            stack.callback(os.close,logfd)
            cowriefd=os.open("cowrie",directory_flags,dir_fd=logfd)
            stack.callback(os.close,cowriefd)
            try:
                filefd=os.open("cowrie.json",file_flags,dir_fd=cowriefd)
            except FileNotFoundError:
                fail("JSON_LOG_MISSING");return result
            stack.callback(os.close,filefd)
            before=os.fstat(filefd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:
                fail("JSON_LOG_TYPE_UNSAFE");return result
            # Checking only the var directory is unsafe if the log itself is a
            # bind mount from an unbounded host filesystem.
            varspace=os.fstatvfs(rootfd)
            logspace=os.fstatvfs(filefd)
            for space in (varspace,logspace):
                capacity=space.f_blocks*space.f_frsize
                free=space.f_bavail*space.f_frsize
                if capacity<=0 or capacity>capacity_ceiling:fail("VOLUME_LIMIT_NOT_PROVEN")
                if free<min_free:fail("FREE_SPACE_LOW")
            result["capacity_bytes"]=logspace.f_blocks*logspace.f_frsize
            result["free_bytes"]=logspace.f_bavail*logspace.f_frsize
            if before.st_size<=0:fail("JSON_LOG_EMPTY");return result
            if before.st_size>max_log:fail("JSON_LOG_TOO_LARGE");return result
            # The dup is owned by the stream, the pinned descriptor by ExitStack.
            seen_event_lines=set()
            with os.fdopen(os.dup(filefd),"rb") as stream:
                while True:
                    line=stream.readline(MAX_LINE+2)
                    if not line:break
                    if len(line)>MAX_LINE or not line.endswith(b"\n"):
                        fail("JSON_LINE_INVALID");break
                    try:item=json.loads(line)
                    except (ValueError,UnicodeError):
                        fail("JSON_LINE_INVALID");break
                    if not isinstance(item,dict) or type(item.get("eventid")) is not str:
                        fail("JSON_EVENT_INVALID");break
                    canonical=json.dumps(item,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
                    line_digest=hashlib.sha256(canonical).digest()
                    if line_digest in seen_event_lines:
                        fail("JSON_LINE_DUPLICATE")
                        break
                    seen_event_lines.add(line_digest)
                    result["log_entries"]+=1
            after=os.fstat(filefd)
            # Reject concurrent append, truncate, replacement or metadata
            # change. This does not resist a privileged attacker forging data.
            fingerprint=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            if fingerprint(before)!=fingerprint(after):
                fail("LOG_CHANGED_WHILE_READING")
            if result["log_entries"]<=0:fail("JSON_LOG_NO_EVENTS")
    except (OSError,ValueError,TypeError,NotImplementedError):
        fail("IO_OR_FORMAT_ERROR")
    result["passed"]=not issues
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--private-var",required=True)
    parser.add_argument("--capacity-ceiling-bytes",type=int,default=DEFAULT_CEILING)
    parser.add_argument("--min-free-bytes",type=int,default=DEFAULT_MIN_FREE)
    parser.add_argument("--max-log-bytes",type=int,default=DEFAULT_MAX_LOG)
    args=parser.parse_args()
    report=assess(args.private_var,args.capacity_ceiling_bytes,args.min_free_bytes,args.max_log_bytes)
    print(json.dumps(report,sort_keys=True))
    return 0 if report["passed"] else 3

if __name__=="__main__":sys.exit(main())
