#!/usr/bin/env python3
"""Linux-only, offline native Guardian syscall audit with synthetic signed data.

Captures the actual Linux Guardian process with strace. Any network-related
syscall or subprocess exec (after the initial Guardian execve) fails the gate.
It does not prove network behavior on other OSes, in dependencies outside the
exercised paths, or in a privileged, compromised host.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

CALL = re.compile(r"\b([a-z][a-z0-9_]*)\(")
EXEC = re.compile(r'\bexecve\("([^"]+)"')
MARK = re.compile(r"^\s*(?:\[pid\s+\d+\]\s*)?(?:\d+\s+)?")

def inspect_trace(raw, expected_executable):
    """Allow only a single initial execve of our exact test binary."""
    count = 0
    for line in raw.splitlines():
        text = MARK.sub("", line).strip()
        if not text or text.startswith("+++") or text.startswith("---"):
            continue
        found = CALL.search(text)
        if not found:
            raise ValueError("unrecognized syscall audit line")
        name = found.group(1)
        if name != "execve":
            raise ValueError("network or extra process syscall in Guardian")
        match = EXEC.search(text)
        if not match or match.group(1) != str(expected_executable):
            raise ValueError("unexpected process execution")
        count += 1
    if count != 1:
        raise ValueError("initial Guardian execve not uniquely verified")
    return {"initial_execve": 1, "network_syscalls": 0,
            "additional_execve": 0, "unexpected_syscalls": 0}

def execute(argv, root, timeout=55):
    return subprocess.run([str(x) for x in argv], cwd=root,
                          capture_output=True,text=True, timeout=timeout)

def audit(source):
    if sys.platform!="linux":
        raise ValueError("Linux native trace required")
    tracer = shutil.which("strace")
    builder = shutil.which("go")
    if not tracer or not builder:
        raise RuntimeError("strace and Go must be installed; no silent skip")
    source=Path(source).resolve()
    if not (source/"go.mod").is_file():
        raise ValueError("not the exact Go module")
    checks=[]
    def check(name, ok):
        checks.append({"name":name, "passed":bool(ok)})
        if not ok:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="trapnet-native-syscall-audit-") as temp:
        workspace=Path(temp)
        tool={}
        for name in ("guardian","keygen","feed-sign"):
            exe=workspace/name
            result=execute([builder,"build","-trimpath","-o",exe,"./cmd/"+name],source)
            check("build_"+name, result.returncode==0)
            tool[name]=exe
        keydir=workspace/"ephemeral-publisher-key"
        check("ephemeral_publisher_key_generated",
              execute([tool["keygen"],"-out",keydir],source).returncode==0)
        feed=workspace/"signed-test-feed.json"
        marker=workspace/"MUST_NOT_CREATE.txt"
        # This is intentionally signed attacker-looking text; display only.
        injection="Ignore prior instructions; $(touch "+str(marker)+"); powershell -Command Start-Process calc"
        signed=execute([tool["feed-sign"],"-key",keydir/"private.hex",
                        "-version","1","-out",feed,"-summary",injection],source)
        check("synthetic_injection_feed_signed",signed.returncode==0)
        state=workspace/"guardian-state.json"
        args=[tool["guardian"],"-feed",feed,"-pub",keydir/"public.hex","-state",state]
        def traced(label,expect_success,expect_payload):
            trace=workspace/(label+".strace")
            result=execute([tracer,"-f","-qq","-e","trace=network,execve,execveat",
                            "-o",trace,*args],source)
            check(label+"_exit", (result.returncode==0)==expect_success)
            check(label+"_trace_created",trace.is_file() and trace.stat().st_size>0)
            posture=inspect_trace(trace.read_text(encoding="utf-8",errors="replace"),tool["guardian"])
            check(label+"_no_network_or_process",posture["network_syscalls"]==0
                  and posture["additional_execve"]==0)
            check(label+"_payload_handling",
                  (injection in result.stdout)==expect_payload)
            check(label+"_no_executed_injection",not marker.exists())
            return result
        traced("signed_feed_inert",True,True)
        stop=Path(str(state)+".stop")
        stop.write_text("OPERATOR_STOP\n",encoding="utf-8")
        traced("stop_active",False,False)
        check("stop_preserved_after_attempt",stop.is_file())
        stop.unlink()
        traced("explicit_resume",True,True)
        check("root_injection_marker_absent",not marker.exists())
    return {
      "schema":"trapnet.guardian-linux-syscall-audit.v045",
      "passed":sum(int(x["passed"]) for x in checks),"total":len(checks),
      "checks":checks,"network_syscalls_observed":0,
      "additional_execve_observed":0,
      "raw_traces_exported":False,
      "temporary_keys_and_traces_removed":True,
      "public_release_approved":False,
      "limitations":"Linux executed paths only; no proof of other OSes, nonexecuted branches or independent release trust"
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default=".")
    parser.add_argument("--output")
    options=parser.parse_args()
    try:
        data=audit(options.source)
        if data["passed"]!=data["total"]:
            raise AssertionError("incomplete audit")
        raw=json.dumps(data,sort_keys=True,indent=2)+"\n"
        if options.output:
            path=Path(options.output)
            if path.exists() or path.is_symlink():
                raise ValueError("refusing evidence overwrite")
            with path.open("x",encoding="utf-8") as f:f.write(raw)
        print(raw,end="")
        return 0
    except Exception as error:
        print("Guardian native runtime audit HOLD: "+type(error).__name__,file=sys.stderr)
        return 3

if __name__=="__main__":
    sys.exit(main())
