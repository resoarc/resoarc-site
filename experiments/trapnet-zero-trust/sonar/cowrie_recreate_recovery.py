#!/usr/bin/env python3
"""DISPOSABLE offline Cowrie remove/recreate and SIGKILL recovery trial.

Does not use the running production Cowrie, production binds, real attacks,
public ports or host-network access. Only accepts pre-existing immutable image
IDs. Must be invoked by an authorized operator on a Linux Docker test host.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import uuid

from cowrie_offline_integration import (
    BASE, docker, image_verified, initialize_var, ssh_probe, json_events,
    confirm_isolation,
)

def snapshot(data):
    file = data / "log/cowrie/cowrie.json"
    if not file.is_file() or file.is_symlink():
        raise ValueError("JSON audit log absent or symlinked")
    content = file.read_bytes()
    if len(content) > 4 * 1024 * 1024:
        raise ValueError("test log exceeds safety cap; no automatic truncation")
    total, has_connect = json_events(data)
    connections = sum(
        json.loads(line).get("eventid") == "cowrie.session.connect"
        for line in content.splitlines() if line.strip()
    )
    if not(total > 0 and has_connect and connections > 0):
        raise ValueError("no valid SSH session evidence")
    return content, total, connections

def verify_log_continuity(previous, data):
    latest, count, connections = snapshot(data)
    if not latest.startswith(previous):
        raise ValueError("audit log truncated or rewritten")
    return latest, count, connections

def default_config_is_regular(root):
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            p = Path(directory) / name
            if p.is_symlink():
                raise ValueError("default config contains symlink")
            if not (p.is_file() or p.is_dir()):
                raise ValueError("unexpected image default file type")

def trial(image, delay=5):
    image_verified(image)
    root = Path(tempfile.mkdtemp(prefix="trapnet-cowrie-recreate-", dir="/tmp"))
    os.chmod(root, 0o700)
    name = "trapnet-cowrie-recovery-lab-" + uuid.uuid4().hex[:12]
    preflight = name+"-defaults"
    active = []
    stage="prepare"
    result = {
        "schema":"trapnet.cowrie-offline-recreate.v1",
        "passed":False,"cleanup":False,"production_modified":False,
        "public_ports":0,"network":"none",
        "config_read_only":False,"root_read_only":False,
        "original_ssh":False,"recreated_ssh":False,"sigkill_recovery":False,
        "log_continuity_after_remove":False,"log_continuity_after_sigkill":False,
        "fresh_container_identity":False,"error_class":None,"failure_stage":None,
        "size_check_only_not_quota":True,
    }
    def create():
        docker("create","--name",name,"--network","none","--read-only",
               "--user","999:999","--cap-drop","ALL",
               "--security-opt","no-new-privileges","--pids-limit","64",
               "--memory","192m","--cpus","0.5",
               "--tmpfs","/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777",
               "--mount",f"type=bind,src={config},dst={BASE}/etc,readonly",
               "--mount",f"type=bind,src={data},dst={BASE}/var",
               image)
        active.append(name)
    def start():
        docker("start",name)
        time.sleep(delay)
        if not confirm_isolation(name,image,config,data):
            raise ValueError("isolation or startup failure")
        return json.loads(docker("inspect",name).stdout)[0]["Id"]
    try:
        config=root/"etc"; data=root/"var"
        config.mkdir(mode=0o700)
        stage="extract_image_defaults"
        docker("create","--name",preflight,"--network","none",image)
        active.append(preflight)
        docker("cp",preflight+":"+BASE+"/etc/.",str(config))
        docker("rm","-v",preflight)
        active.remove(preflight)
        default_config_is_regular(config)
        os.chmod(config,0o755)
        initialize_var(data)
        stage="first_start"
        create()
        original_id=start()
        result["root_read_only"]=True
        result["config_read_only"]=True
        result["original_ssh"]=ssh_probe(name)
        time.sleep(1.5)
        first, count1, c1=snapshot(data)
        result["first_events"]=count1
        if not result["original_ssh"]:
            raise ValueError("original SSH banner failed")
        stage="remove_and_recreate"
        docker("stop","--time","5",name)
        docker("rm","-v",name)
        active.remove(name)
        # Container deletion must NOT mutate/erase separately owned test data.
        pre_recreate,_,_=verify_log_continuity(first,data)
        create()
        new_id=start()
        result["fresh_container_identity"]=new_id!=original_id
        result["recreated_ssh"]=ssh_probe(name)
        time.sleep(1.5)
        second, count2, c2=verify_log_continuity(pre_recreate,data)
        result["after_recreate_events"]=count2
        result["log_continuity_after_remove"]=count2>count1 and c2>c1
        if not all(result[k] for k in
                   ("fresh_container_identity","recreated_ssh","log_continuity_after_remove")):
            raise ValueError("delete/recreate verification failed")
        stage="forced_termination"
        docker("kill","--signal","SIGKILL",name)
        # Kill might create a final log line but must not remove existing ones.
        pre_crash,_,_=verify_log_continuity(second,data)
        start()
        result["sigkill_recovery"]=ssh_probe(name)
        time.sleep(1.5)
        third,count3,c3=verify_log_continuity(pre_crash,data)
        result["after_sigkill_events"]=count3
        result["log_continuity_after_sigkill"]=count3>count2 and c3>c2
        if not(result["sigkill_recovery"] and result["log_continuity_after_sigkill"]):
            raise ValueError("SIGKILL recovery failed")
        # This is an observation cap only, not real disk quota enforcement.
        bytes_used=sum((Path(path)/file).stat().st_size
            for path,dirs,files in os.walk(data) for file in files)
        result["private_var_bytes"]=bytes_used
        if bytes_used > 4*1024*1024:
            raise ValueError("disposable test data exceeded cap")
        result["passed"]=True
    except Exception as error:
        result["error_class"]=type(error).__name__
        result["failure_stage"]=stage
    finally:
        cleaned=True
        for container in reversed(active):
            cleaned &= docker("rm","-f","-v",container,check=False).returncode==0
        if cleaned:
            try:shutil.rmtree(root)
            except OSError:cleaned=False
        result["cleanup"]=cleaned
        result["passed"]=result["passed"] and cleaned
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--image-id",required=True)
    parser.add_argument("--delay",type=float,default=5)
    args=parser.parse_args()
    if not 1<=args.delay<=15:parser.error("delay must be 1..15 seconds")
    try:
        result=trial(args.image_id,args.delay)
    except Exception as exc:
        result={"schema":"trapnet.cowrie-offline-recreate.v1",
                "passed":False,"error_class":type(exc).__name__}
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result.get("passed") is True else 3

if __name__=="__main__":sys.exit(main())
