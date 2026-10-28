#!/usr/bin/env python3
"""Read-only, fail-closed Cowrie *local* release preflight.

Assesses Docker containment and actual bounded persistent log filesystem.
No shell, exec, network requests, container or file mutations. Docker CLI
inspect uses only read calls. A passing local result is NOT release approval.
Never prints paths, IPs, raw events, credentials or host inventory.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import cowrie_log_health

SCHEMA="trapnet.cowrie-local-release-preflight.v1"
_IMAGE_ID=re.compile(r"^sha256:[0-9a-f]{64}$")
_IMMUTABLE_SOURCE=re.compile(r"^(?:sha256:[0-9a-f]{64}|[a-zA-Z0-9._:/-]+@sha256:[0-9a-f]{64})$")

def assess_config(obj,network_internal,file_health):
    issues=set()
    def reject(code):issues.add(code)
    if not isinstance(obj,dict) or not isinstance(obj.get("HostConfig"),dict):
        return {"schema":SCHEMA,"local_preflight_pass":False,"issues":["CONTAINER_INSPECT_UNAVAILABLE"],
                "production_release_approved":False,"feed_publishable":False}
    host=obj["HostConfig"]
    config=obj.get("Config") or {}
    state=obj.get("State") or {}
    if state.get("Running") is not True:reject("CONTAINER_NOT_RUNNING")
    user=config.get("User")
    if not isinstance(user,str) or not user or user in ("0","0:0","root","root:root") or user.split(":")[0]=="0":
        reject("ROOT_USER_NOT_EXCLUDED")
    image=obj.get("Image")
    if not isinstance(image,str) or not _IMAGE_ID.fullmatch(image):
        reject("IMMUTABLE_IMAGE_ID_NOT_CONFIRMED")
    configured_image=config.get("Image")
    # Docker inspect alone cannot prove the declarative deployment file is pinned.
    if not isinstance(configured_image,str) or not _IMMUTABLE_SOURCE.fullmatch(configured_image):
        reject("IMMUTABLE_DEPLOYMENT_REFERENCE_NOT_PROVEN")
    if host.get("Privileged") is not False:reject("PRIVILEGED_NOT_DISABLED")
    if not host.get("ReadonlyRootfs"):reject("WRITABLE_CONTAINER_ROOT")
    if host.get("PortBindings"):reject("PORTS_PUBLISHED")
    if not isinstance(host.get("CapDrop"),list) or "ALL" not in host["CapDrop"]:
        reject("CAPABILITIES_NOT_DROPPED")
    if not any(opt in ("no-new-privileges", "no-new-privileges:true") for opt in (host.get("SecurityOpt") or [])):
        reject("PRIVILEGE_ESCALATION_NOT_DISABLED")
    limits=[("Memory",32*1024*1024,256*1024*1024,"MEMORY_NOT_BOUNDED"),
            ("NanoCpus",1000000,500000000,"CPU_NOT_BOUNDED"),
            ("PidsLimit",1,128,"PIDS_NOT_BOUNDED")]
    for key,lo,hi,code in limits:
        value=host.get(key)
        if type(value) is not int or not lo<=value<=hi:reject(code)
    network_mode=host.get("NetworkMode")
    if network_mode!="none" and network_internal is not True:
        reject("NETWORK_NOT_INTERNAL")
    if not isinstance(network_mode,str) or network_mode in ("host","bridge"):
        reject("NETWORK_ISOLATION_NOT_PROVEN")
    if any("docker.sock" in (m.get("Destination") or "") for m in obj.get("Mounts",[]) if isinstance(m,dict)):
        reject("DOCKER_SOCKET_MOUNT")
    log=host.get("LogConfig") or {}
    # Container stdout logs should also be bounded; Cowrie JSON files are
    # assessed independently by cowrie_log_health.
    settings=log.get("Config") or {}
    if log.get("Type") not in ("json-file","local"):
        reject("DOCKER_LOG_DRIVER_NOT_BOUNDED")
    def positive_int(s):
        try:return int(s)>0 and str(int(s))==str(s)
        except (ValueError,TypeError,OverflowError):return False
    size=settings.get("max-size")
    if not isinstance(size,str) or not re.fullmatch(r"[1-9][0-9]*[kKmMgG]?",size):
        reject("DOCKER_LOG_ROTATION_NOT_PROVEN")
    if not positive_int(settings.get("max-file")) or int(settings.get("max-file","0"))>8:
        reject("DOCKER_LOG_ROTATION_NOT_PROVEN")
    if not isinstance(file_health,dict) or file_health.get("passed") is not True:
        reject("PERSISTENT_LOG_CAPACITY_NOT_PROVEN")
    # Avoid falsely declaring authorized external review, network egress
    # isolation, feed signatures or off-host backup from local observations.
    return {"schema":SCHEMA,"local_preflight_pass":not issues,
            "issues":sorted(issues),"production_release_approved":False,
            "feed_publishable":False,
            "requires_external_witness_and_human_review":True,
            "raw_telemetry_exported":False}

def _docker_inspect(*args):
    p=subprocess.run(["docker","inspect",*args],
        capture_output=True,text=True,timeout=12,check=False)
    if p.returncode:raise ValueError("docker inspect failed")
    objs=json.loads(p.stdout)
    if not isinstance(objs,list) or len(objs)!=1 or not isinstance(objs[0],dict):
        raise ValueError("unexpected Docker metadata")
    return objs[0]

def _mounted_var_matches(obj,private_var):
    """The checked private var MUST be the running Cowrie's writable var mount."""
    path=Path(private_var)
    if path.is_symlink() or not path.is_dir():
        return False
    matches=[m for m in (obj.get("Mounts") or [])
        if isinstance(m,dict) and m.get("Destination")=="/cowrie/cowrie-git/var"]
    if len(matches)!=1:return False
    mount=matches[0]
    if mount.get("Type") not in ("bind","volume") or mount.get("RW") is not True:
        return False
    source=mount.get("Source")
    if not isinstance(source,str) or not source:
        return False
    return os.path.samefile(source,path)

def inspect_local(container,private_var):
    try:
        obj=_docker_inspect(container)
        mode=(obj.get("HostConfig") or {}).get("NetworkMode")
        if mode=="none":
            internal=True
        elif isinstance(mode,str) and re.fullmatch(r"[a-zA-Z0-9_.-]{1,80}",mode):
            p=subprocess.run(["docker","network","inspect",mode],
                capture_output=True,text=True,timeout=12,check=False)
            if p.returncode:raise ValueError("network metadata failed")
            net=json.loads(p.stdout)
            internal=(len(net)==1 and net[0].get("Internal") is True)
        else:internal=False
        log_health=cowrie_log_health.assess(private_var)
        verdict=assess_config(obj,internal,log_health)
        if not _mounted_var_matches(obj,private_var):
            verdict["issues"]=sorted(set(verdict["issues"]+["LOG_VOLUME_SOURCE_NOT_CONFIRMED"]))
            verdict["local_preflight_pass"]=False
        return verdict
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):
        return {"schema":SCHEMA,"local_preflight_pass":False,
                "issues":["READONLY_INSPECTION_UNAVAILABLE"],
                "production_release_approved":False,
                "feed_publishable":False,"raw_telemetry_exported":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--container",default="trapnet-cowrie-stage")
    parser.add_argument("--private-var",required=True)
    options=parser.parse_args()
    r=inspect_local(options.container,options.private_var)
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))
    return 0 if r.get("local_preflight_pass") else 3

if __name__=="__main__":sys.exit(main())
