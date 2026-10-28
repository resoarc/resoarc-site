#!/usr/bin/env python3
"""Only fill an 8MiB uniquely-named Docker tmpfs with synthetic bytes.

Run on an explicitly authorized Linux Docker lab host. Never mount production
data, never pull an image, publish a port, or connect to an external network.
The result is diagnostic: SSH may remain alive even when logs are unsafe.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from cowrie_offline_integration import BASE,docker,image_verified

def probe_private_log_health(container):
    """Pass local trusted checker to the isolated container via stdin only."""
    source_path=Path(__file__).with_name("cowrie_log_health.py")
    if source_path.is_symlink() or not source_path.is_file() or source_path.stat().st_size>16384:
        raise ValueError("missing or unsafe log-health checker")
    source=source_path.read_text(encoding="utf-8")
    result=subprocess.run(
        ["docker","exec","-i",container,PYTHON,"-","--private-var",BASE+"/var"],
        input=source,capture_output=True,text=True,timeout=15)
    if result.returncode not in (0,3):
        raise RuntimeError("log health checker failed unexpectedly")
    payload=json.loads(result.stdout)
    if payload.get("schema")!="trapnet.cowrie-log-health.v1":
        raise ValueError("wrong health report schema")
    return result.returncode==0,payload

CAP=8*1024*1024
PYTHON="/cowrie/cowrie-env/bin/python3"

def isolated_outcome(image):
    image_verified(image)
    tag=uuid.uuid4().hex[:10]
    volume="trapnet-pressure-"+tag
    prep="trapnet-pressure-init-"+tag
    cowrie="trapnet-pressure-cowrie-"+tag
    source="trapnet-pressure-default-"+tag
    scratch=Path(tempfile.mkdtemp(prefix="trapnet-pressure-etc-",dir="/tmp"))
    created=[];volume_created=False
    result={"schema":"trapnet.cowrie-bounded-pressure.v1",
            "passed":False,"cleanup":False,"production_modified":False,
            "network":"none","public_ports":0,"release_approved":False,
            "enospc":False,"cap_verified":False,"ssh_after_pressure":False,
            "log_append_after_pressure":False,"logging_recovers_after_free":False,
            "error_class":None}
    def call(*args):
        return docker(*args,check=False)
    def exec_python(script):
        proc=call("exec",cowrie,PYTHON,"-c",script)
        if proc.returncode:raise RuntimeError("isolated_python_exec_failed")
        return json.loads(proc.stdout)
    def connect():
        p=call("exec",cowrie,PYTHON,"-c",
          "import socket,time;s=socket.create_connection(('127.0.0.1',2222),timeout=4);s.settimeout(4);b=s.recv(120);s.sendall(b'SSH-2.0-TrapNet-Lab\\r\\n');time.sleep(.2);s.close();print('OK' if b.startswith(b'SSH-2.0-') else 'FAIL')")
        return p.returncode==0 and p.stdout.strip()=="OK"
    def counts():
        return exec_python("""import os,json
p='/cowrie/cowrie-git/var/log/cowrie/cowrie.json'
r={'connections':0,'events':0,'exists':os.path.isfile(p)}
if r['exists']:
 for line in open(p,'rb'):
  try:
   e=json.loads(line);r['events']+=1
   r['connections']+=e.get('eventid')=='cowrie.session.connect'
  except (ValueError,AttributeError):pass
print(json.dumps(r))""")
    try:
        config=scratch/"etc";config.mkdir()
        docker("create","--name",source,"--network","none",image);created.append(source)
        docker("cp",source+":"+BASE+"/etc/.",str(config))
        docker("rm","-v",source);created.remove(source)
        os.chmod(config,0o755)
        docker("volume","create","--driver","local","--opt","type=tmpfs",
               "--opt","device=tmpfs","--opt","o=size=8m,uid=999,gid=999",volume)
        volume_created=True
        init_script="import os,time;b='/cowrie/cowrie-git/var';[os.makedirs(os.path.join(b,x),exist_ok=True) for x in ('log/cowrie','run','lib/cowrie')];time.sleep(90)"
        docker("run","-d","--name",prep,"--network","none","--read-only",
               "--user","999:999","--cap-drop","ALL",
               "--security-opt","no-new-privileges","--memory","64m",
               "--pids-limit","32",
               "--mount",f"type=volume,src={volume},dst={BASE}/var",
               "--entrypoint",PYTHON,image,"-c",init_script)
        created.append(prep)
        time.sleep(1)
        docker("create","--name",cowrie,"--network","none","--read-only",
               "--user","999:999","--cap-drop","ALL",
               "--security-opt","no-new-privileges","--memory","192m",
               "--pids-limit","64",
               "--tmpfs","/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777",
               "--mount",f"type=bind,src={config},dst={BASE}/etc,readonly",
               "--mount",f"type=volume,src={volume},dst={BASE}/var",image)
        created.append(cowrie)
        docker("start",cowrie)
        time.sleep(5)
        first_ssh=connect()
        time.sleep(1.5)
        before=counts()
        before_healthy,before_status=probe_private_log_health(cowrie)
        result["healthy_before_pressure"]=before_healthy
        pressure_script="""import os,json,errno
v=os.statvfs('/cowrie/cowrie-git/var');cap=v.f_blocks*v.f_frsize
if cap!=8388608:
 print(json.dumps({'cap':cap,'enospc':False}));raise SystemExit(2)
hit=False
with open('/cowrie/cowrie-git/var/trapnet-pressure.bin','wb') as stream:
 for i in range(16):
  try:stream.write(b'x'*1048576);stream.flush()
  except OSError as error:
   hit=error.errno==errno.ENOSPC;break
print(json.dumps({'cap':cap,'enospc':hit}))"""
        measured=exec_python(pressure_script)
        result["cap_verified"]=measured.get("cap")==CAP
        result["enospc"]=measured.get("enospc") is True
        result["ssh_after_pressure"]=connect()
        time.sleep(1.5)
        during=counts()
        during_healthy,during_status=probe_private_log_health(cowrie)
        result["capacity_failure_detected"]=(not during_healthy and
            "FREE_SPACE_LOW" in during_status.get("issues",[]))
        result["events_before"]=before["events"]
        result["events_during_pressure"]=during["events"]
        result["log_append_after_pressure"]=during["connections"]>before["connections"]
        exec_python("import os,json;os.unlink('/cowrie/cowrie-git/var/trapnet-pressure.bin');print(json.dumps({'removed':True}))")
        recovered_ssh=connect()
        time.sleep(1.5)
        after=counts()
        after_healthy,after_status=probe_private_log_health(cowrie)
        result["healthy_after_free"]=after_healthy
        result["events_after_free"]=after["events"]
        result["logging_recovers_after_free"]=after["connections"]>during["connections"]
        result["cowrie_still_running"]=json.loads(docker("inspect",cowrie).stdout)[0]["State"]["Running"]
        # The lab itself succeeds if it demonstrates bounded ENOSPC and
        # observes all stages, not because a production safety policy is proven.
        result["passed"]=bool(first_ssh and before["connections"]>0 and
                              result["cap_verified"] and result["enospc"] and
                              result["ssh_after_pressure"] and recovered_ssh and
                              result["logging_recovers_after_free"] and
                              result["healthy_before_pressure"] and
                              result["capacity_failure_detected"] and
                              result["healthy_after_free"])
    except Exception as error:
        result["error_class"]=type(error).__name__
    finally:
        cleaned=True
        for item in reversed(created):
            cleaned &= call("rm","-f","-v",item).returncode==0
        if volume_created:cleaned &= call("volume","rm",volume).returncode==0
        try:shutil.rmtree(scratch)
        except OSError:cleaned=False
        result["cleanup"]=cleaned
        result["passed"]=result["passed"] and cleaned
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--image-id",required=True)
    args=parser.parse_args()
    try:result=isolated_outcome(args.image_id)
    except Exception as error:
        result={"schema":"trapnet.cowrie-bounded-pressure.v1",
                "passed":False,"error_class":type(error).__name__}
    print(json.dumps(result,sort_keys=True))
    return 0 if result.get("passed") else 3

if __name__=="__main__":sys.exit(main())
