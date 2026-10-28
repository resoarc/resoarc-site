#!/usr/bin/env python3
"""TrapNet local-only periodic privacy snapshot. Raw Docker logs remain in memory."""
import json
import os
import pathlib
import subprocess
import tempfile
import sonar_hardening

ROOT=pathlib.Path("/opt/resoarc-trapnet")
REPORT=ROOT/"operational"/"sonar"/"privacy_latest.json"

def collect():
    try:
        proc=subprocess.run(
            ["docker","logs","--tail","400","trapnet-web-stage"],
            capture_output=True,text=True,timeout=5,check=False)
        if proc.returncode!=0:
            records=[]
            status="log_unavailable"
        else:
            records=proc.stdout.splitlines()[:400]
            status="available"
    except (OSError,subprocess.TimeoutExpired):
        records=[]
        status="log_unavailable"
    report=sonar_hardening.aggregate(records)
    report["log_source_status"]=status
    report["coverage"]=sonar_hardening.coverage()
    report["feed_status"]="NOT_SIGNED_NOT_DISTRIBUTED"
    return report

def main():
    report=collect()
    REPORT.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(REPORT.parent,0o700)
    fd,temp=tempfile.mkstemp(prefix=".sonar-tmp-",dir=str(REPORT.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as stream:
            json.dump(report,stream,ensure_ascii=False,sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp,0o600)
        os.replace(temp,REPORT)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    print(json.dumps({"ok":True,"source":report["log_source_status"],
                      "no_sensitive_fields":True,"automatic_blocking":False}))

if __name__=="__main__":main()
