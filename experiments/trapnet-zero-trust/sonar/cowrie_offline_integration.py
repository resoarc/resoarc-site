#!/usr/bin/env python3
"""Cowrie disposable offline integration test. Never modifies production containers.

Root-run Linux host with authorized Docker required. The image MUST already be
installed and selected by immutable sha256 image ID. The container has no
network, no published ports and no original host config/log mounts.
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

BASE = "/cowrie/cowrie-git"
USER = 999

def docker(*args, check=True, timeout=30):
    p = subprocess.run(["docker",*map(str,args)],capture_output=True,
                       text=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError("docker command failed: "+str(args[0]))
    return p

def image_verified(image):
    if not image.startswith("sha256:") or len(image)!=71 or any(c not in "0123456789abcdef" for c in image[7:]):
        raise ValueError("immutable existing sha256 image ID required")
    payload=json.loads(docker("image","inspect",image).stdout)
    if len(payload)!=1 or payload[0].get("Id")!=image:
        raise ValueError("image ID mismatch")
    declared=set((payload[0].get("Config") or {}).get("Volumes") or {})
    if declared != {BASE+"/etc",BASE+"/var"}:
        raise ValueError("unexpected declared image volumes")
    return image

def initialize_var(directory):
    directory.mkdir(mode=0o700)
    for sub in ("log/cowrie","run","lib/cowrie"):
        (directory/sub).mkdir(mode=0o700,parents=True)
    for root, dirs, files in os.walk(directory):
        os.chown(root,USER,USER)
        for f in files: os.chown(os.path.join(root,f),USER,USER)

def ssh_probe(name):
    client=(
        "import socket,time;"
        "s=socket.create_connection(('127.0.0.1',2222),timeout=4);"
        "s.settimeout(4);b=s.recv(120);"
        "assert b.startswith(b'SSH-2.0-');"
        "s.sendall(b'SSH-2.0-TrapNet-Offline-Tester\\r\\n');"
        "time.sleep(.3);s.close();print('SSH_OK')"
    )
    p=docker("exec",name,"/cowrie/cowrie-env/bin/python3","-c",client,
             timeout=12,check=False)
    return p.returncode==0 and "SSH_OK" in p.stdout

def json_events(directory):
    file=directory/"log/cowrie/cowrie.json"
    if not file.is_file() or file.is_symlink():return (0,False)
    seen=0;connected=False
    for line in file.read_bytes().splitlines():
        if not line.strip():continue
        if len(line)>65536:raise ValueError("oversize JSON event")
        obj=json.loads(line)
        if not isinstance(obj,dict) or not isinstance(obj.get("eventid"),str):
            raise ValueError("invalid event schema")
        seen+=1
        connected |= obj["eventid"]=="cowrie.session.connect"
    return seen,connected

def confirm_isolation(name,image,config,data):
    container=json.loads(docker("inspect",name).stdout)[0]
    host=container["HostConfig"]
    mounts={m["Destination"]:m for m in container.get("Mounts",[])}
    if container["Image"]!=image or host.get("NetworkMode")!="none" or host.get("ReadonlyRootfs") is not True:
        raise ValueError("network/root filesystem isolation not enforced")
    if (host.get("Privileged") or host.get("CapAdd") or host.get("PortBindings")
        or "ALL" not in (host.get("CapDrop") or [])
        or not any("no-new-privileges" in x for x in (host.get("SecurityOpt") or []))
        or host.get("PidsLimit",0)<=0 or host.get("Memory",0)<=0):
        raise ValueError("privilege or limits not enforced")
    if (set(mounts)!={BASE+"/etc",BASE+"/var"}
        or mounts[BASE+"/etc"]["RW"] is not False
        or mounts[BASE+"/var"]["RW"] is not True
        or mounts[BASE+"/etc"]["Source"]!=str(config)
        or mounts[BASE+"/var"]["Source"]!=str(data)):
        raise ValueError("private mounts are not as requested")
    return container["State"]["Running"]

def trial(image,delay=5):
    image_verified(image)
    base=Path(tempfile.mkdtemp(prefix="trapnet-cowrie-offline-",dir="/tmp"))
    os.chmod(base,0o700)
    name="trapnet-cowrie-lab-"+uuid.uuid4().hex[:12]
    staging=name+"-defaults"
    created=[]
    result={"schema":"trapnet.cowrie.offline-integration.v1",
            "image_id":image,"public_ports":0,"network":"none",
            "production_modified":False,"test_log_contents_exported":False,
            "read_only_root":False,"config_read_only":False,
            "ssh_banner":False,"json_log":False,"restart":False,
            "persistent_json_log":False,"passed":False,"error_class":None,
            "failure_stage":None,"cleanup":False}
    stage="prepare"
    try:
        config=base/"etc";data=base/"var";config.mkdir(mode=0o700)
        # Copy only image defaults from an unstarted, disconnected container.
        docker("create","--name",staging,"--network","none",image)
        created.append(staging)
        docker("cp",staging+":"+BASE+"/etc/.",str(config))
        docker("rm","-v",staging);created.remove(staging)
        for directory,_,files in os.walk(config):
            if any((Path(directory)/f).is_symlink() for f in files):
                raise ValueError("symlink in image default config")
        os.chmod(config,0o755)
        initialize_var(data)
        stage="start"
        docker("create","--name",name,"--network","none","--read-only",
               "--user","999:999","--cap-drop","ALL",
               "--security-opt","no-new-privileges","--pids-limit","64",
               "--memory","192m","--cpus","0.5",
               "--tmpfs","/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777",
               "--mount",f"type=bind,src={config},dst={BASE}/etc,readonly",
               "--mount",f"type=bind,src={data},dst={BASE}/var",image)
        created.append(name)
        docker("start",name);time.sleep(delay)
        result["read_only_root"]=confirm_isolation(name,image,config,data)
        result["config_read_only"]=True
        stage="connect_and_log"
        result["ssh_banner"]=ssh_probe(name);time.sleep(1.5)
        count,conn=json_events(data)
        result["events_before_restart"]=count
        result["json_log"]=count>0 and conn
        if not(result["read_only_root"] and result["ssh_banner"] and result["json_log"]):
            raise ValueError("Cowrie SSH/JSON not operational")
        stage="restart"
        docker("stop","--time","5",name)
        docker("start",name);time.sleep(delay)
        result["restart"]=confirm_isolation(name,image,config,data) and ssh_probe(name)
        time.sleep(1.5)
        after,has_conn=json_events(data)
        result["events_after_restart"]=after
        result["persistent_json_log"]=after>count and has_conn
        result["passed"]=all(result[k] for k in ("read_only_root","config_read_only",
                  "ssh_banner","json_log","restart","persistent_json_log"))
    except Exception as e:
        result["error_class"]=type(e).__name__
        result["failure_stage"]=stage
    finally:
        cleanup=True
        for container in reversed(created):
            cleanup &= docker("rm","-f","-v",container,check=False).returncode==0
        if cleanup:
            try:shutil.rmtree(base)
            except OSError:cleanup=False
        result["cleanup"]=cleanup
        result["passed"] &= cleanup
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--image-id",required=True)
    parser.add_argument("--delay",type=float,default=5)
    args=parser.parse_args()
    if not(1<=args.delay<=15):parser.error("delay must be 1..15 seconds")
    try:r=trial(args.image_id,args.delay)
    except Exception as error:
        r={"schema":"trapnet.cowrie.offline-integration.v1",
           "passed":False,"error_class":type(error).__name__}
    print(json.dumps(r,sort_keys=True,indent=2))
    return 0 if r["passed"] else 3

if __name__=="__main__":sys.exit(main())
