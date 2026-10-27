#!/usr/bin/env python3
"""TrapNet read-only container boundary assessment (no deploy, no networking).

Docker inspect may contain secrets in Config.Env. This tool never prints or
saves raw inspect JSON. It emits only named boolean controls and verdicts.
Docker inspect cannot prove firewall egress, namespace escape resistance or
the absence of unlisted services. A live isolation test remains mandatory.
"""
import argparse
import json
import re
import subprocess
import sys

ROLES = ("web", "ssh", "edge")
CONTROLS = (
    "running", "unprivileged", "nonroot_user", "all_capabilities_dropped",
    "no_added_capabilities", "no_new_privileges", "not_host_network",
    "docker_socket_absent", "memory_limit_set", "cpu_limit_set",
    "pid_limit_set", "readonly_root", "writable_mounts_scoped",
    "tmpfs_scoped", "namespaces_and_devices_private",
)

WRITE_ALLOWLIST = {"web": set(), "ssh": {"/cowrie/cowrie-git/var"}, "edge": set()}

def _scoped_mounts(mounts, role):
    if role not in WRITE_ALLOWLIST or not isinstance(mounts,list):
        return False
    allowed=WRITE_ALLOWLIST[role]
    seen=set()
    for m in mounts:
        if not isinstance(m,dict):
            return False
        dest=m.get("Destination")
        kind=m.get("Type")
        if type(dest) is not str or not dest.startswith("/") or kind not in ("bind","volume","tmpfs"):
            return False
        if dest in seen:
            return False
        seen.add(dest)
        if m.get("RW") is True and dest not in allowed:
            return False
        if m.get("RW") is not True and m.get("RW") is not False:
            return False
    return True

def _safe_tmpfs(entries, role):
    if entries is None:
        return True
    if not isinstance(entries, dict) or role not in WRITE_ALLOWLIST:
        return False
    paths = {"/tmp": 64 * 1024 * 1024}
    if role == "ssh":
        paths["/cowrie/cowrie-git/var"] = 128 * 1024 * 1024
    for path, settings in entries.items():
        if path not in paths or not isinstance(settings, str):
            return False
        flags = settings.lower().split(",")
        if any(not flag or flag != flag.strip() for flag in flags):
            return False
        if not {"nosuid", "nodev", "noexec"}.issubset(set(flags)):
            return False
        matches = [re.fullmatch(r"size=([1-9][0-9]*)([kmg]?)", flag)
                   for flag in flags if flag.startswith("size=")]
        if len(matches) != 1 or matches[0] is None:
            return False
        value, unit = matches[0].groups()
        scale = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[unit]
        if int(value) * scale > paths[path]:
            return False
        if any(flag in ("dev", "suid", "exec") for flag in flags):
            return False
    return True

def _private_namespaces_and_devices(host):
    return (
        host.get("IpcMode") in ("", "private", None)
        and host.get("PidMode") in ("", "private", None)
        and host.get("UsernsMode") in ("", "private", None)
        and host.get("CgroupnsMode") in ("", "private", None)
        and host.get("UTSMode") in ("", "private", None)
        and not host.get("Devices")
        and not host.get("DeviceRequests")
        and not host.get("VolumesFrom")
        and not host.get("DeviceCgroupRules")
    )

def audit_one(container, role="web"):
    host=container.get("HostConfig") or {}
    conf=container.get("Config") or {}
    state=container.get("State") or {}
    mounts=container.get("Mounts") or []
    sec=host.get("SecurityOpt") or []
    capdrop=host.get("CapDrop") or []
    capadd=host.get("CapAdd") or []
    user=str(conf.get("User") or "").strip().lower()
    network=str(host.get("NetworkMode") or "").lower()
    memory=host.get("Memory") or 0
    pids=host.get("PidsLimit") or 0
    nano=host.get("NanoCpus") or 0
    quota=host.get("CpuQuota") or 0
    period=host.get("CpuPeriod") or 0
    checks={
      "running":state.get("Running") is True,
      "unprivileged":host.get("Privileged") is False,
      "nonroot_user":user not in ("","root","0","0:0") and not user.startswith("0:"),
      "all_capabilities_dropped":"ALL" in capdrop,
      "no_added_capabilities":not capadd,
      "no_new_privileges":any(str(x).lower().startswith("no-new-privileges") for x in sec),
      "not_host_network":network not in ("","host") and not network.startswith("container:"),
      "docker_socket_absent":not any(
           "/var/run/docker.sock" in str(x.get(k) or "") or
           "/run/docker.sock" in str(x.get(k) or "")
           for x in mounts for k in ("Source","Destination")
      ),
      "memory_limit_set":isinstance(memory,int) and memory>0,
      "cpu_limit_set":(isinstance(nano,int) and nano>0) or
           (isinstance(quota,int) and quota>0 and isinstance(period,int) and period>0),
      "pid_limit_set":isinstance(pids,int) and pids>0,
      "readonly_root":host.get("ReadonlyRootfs") is True,
      "writable_mounts_scoped":_scoped_mounts(mounts,role),
      "tmpfs_scoped":_safe_tmpfs(host.get("Tmpfs"),role),
      "namespaces_and_devices_private":_private_namespaces_and_devices(host),
    }
    return checks

def assess(inspections):
    if not isinstance(inspections,dict) or set(inspections)!=set(ROLES):
        raise ValueError("exactly one inspected container for each required role")
    results={}
    for role in ROLES:
        obj=inspections[role]
        if not isinstance(obj,dict):raise ValueError("invalid inspect payload")
        tests=audit_one(obj,role)
        results[role]={"passed":sum(tests.values()),"total":len(CONTROLS),
                       "checks":tests,"failed":[k for k,v in tests.items() if not v]}
    allpass=all(not results[role]["failed"] for role in ROLES)
    return {"schema":"trapnet.sonar-containment-audit.v1",
            "passed_static_container_controls":allpass,
            "public_beta_ready":False,
            "physical_network_containment_verified":False,
            "real_egress_firewall_verified":False,
            "destructive_recovery_verified":False,
            "operational_secrets_exported":False,
            "roles":results,
            "notice":"A green inspect-only audit never proves escape resistance or authorizes release."}

def live(names):
    inspections={}
    for role,name in names.items():
        if not name or len(name)>128 or not all(c.isalnum() or c in "-_." for c in name):
            raise ValueError("invalid container name")
        result=subprocess.run(["docker","inspect",name],capture_output=True,text=True,
                              timeout=12,check=False)
        if result.returncode!=0:raise RuntimeError("one or more containers unavailable")
        data=json.loads(result.stdout)
        if not isinstance(data,list) or len(data)!=1:raise ValueError("invalid docker inspect")
        inspections[role]=data[0]
    return inspections

if __name__=="__main__":
    p=argparse.ArgumentParser()
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--input",help="PRIVATE raw docker inspect fixture (do not publish)")
    group.add_argument("--live",action="store_true",help="local read-only docker inspect")
    p.add_argument("--web",default="trapnet-web-stage")
    p.add_argument("--ssh",default="trapnet-cowrie-stage")
    p.add_argument("--edge",default="trapnet-edge-stage")
    args=p.parse_args()
    try:
        if args.live:
            inspect=live({"web":args.web,"ssh":args.ssh,"edge":args.edge})
        else:
            # Input may contain sensitive env fields. Never echo or save it.
            with open(args.input,encoding="utf-8") as stream:inspect=json.load(stream)
        outcome=assess(inspect)
        print(json.dumps(outcome,sort_keys=True,indent=2))
        sys.exit(0 if outcome["passed_static_container_controls"] else 3)
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
        print("Sonar containment audit refused: "+type(error).__name__,file=sys.stderr)
        sys.exit(2)