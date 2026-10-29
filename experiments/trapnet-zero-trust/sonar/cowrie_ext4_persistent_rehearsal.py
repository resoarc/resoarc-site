#!/usr/bin/env python3
"""TrapNet v0.40: DISPOSABLE bounded *persistent* ext4 Cowrie exercise.

An isolated 16MiB loop-backed ext4 image proves that var/log/cowrie is
genuinely bounded and survives full-container removal and an unmount/remount.
Never mounts, modifies, or backs up production data. No published ports,
network=none, immutable preinstalled Docker image, strict cleanup.

This is an operator-run Linux test. It is NOT a production migration tool.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from cowrie_offline_integration import BASE, docker, image_verified
from cowrie_log_health import assess
from cowrie_lab_backup import copy_verified, manifest
from cowrie_release_preflight import inspect_local

CAPACITY=16*1024*1024
IMAGE_DEFAULT="sha256:17191d19f02bb9b9d9ebda0578f96bd13f764c10a7b5c11a1b50f6eb6c973a9a"

def safe_run(args,timeout=30):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("command failed: "+str(args[0]))
    return p

def log_snapshot(log):
    if not log.is_file() or log.is_symlink():
        raise RuntimeError("missing or unsafe synthetic log")
    content=log.read_bytes()
    if not 0<len(content)<2*1024*1024 or not content.endswith(b"\n"):
        raise RuntimeError("synthetic log invalid size or trailing line")
    count=0
    for line in content.splitlines():
        record=json.loads(line)
        if not isinstance(record,dict) or not isinstance(record.get("eventid"),str):
            raise RuntimeError("invalid synthetic event")
        count+=1
    return content,count

def trial(image,storage_parent=None,wait_sec=3,failure_hook=None,recovery_hook=None,fault_hook=None):
    image_verified(image)
    if os.geteuid()!=0 or not sys.platform.startswith("linux"):
        raise RuntimeError("authorized Linux root only")
    if storage_parent is None:storage_parent="/opt/resoarc-trapnet/staging"
    parent=Path(storage_parent)
    if not parent.is_absolute() or parent.is_symlink() or not parent.is_dir():
        raise RuntimeError("unsafe test parent")
    if str(parent.resolve()) in ("/", "/opt/resoarc-trapnet", "/opt/resoarc-trapnet/var"):
        raise RuntimeError("unsafe test parent")
    root=Path(tempfile.mkdtemp(prefix="trapnet-ext4-private-",dir=str(parent)))
    root.chmod(0o700)
    disk=root/"disk.img"
    mountpoint=root/"mnt"
    mountpoint.mkdir(mode=0o700)
    offvolume=root/"pre-failure-full-var"
    name="trapnet-ext4-lab-"+uuid.uuid4().hex[:10]
    created=False
    mounted=False
    report={"schema":"trapnet.cowrie-bounded-persistent-ext4.v040",
        "passed":False,"production_modified":False,"public_ports":0,"network":"none",
        "capacity_target_bytes":CAPACITY,"backup_verified":False,"recreate_verified":False,
        "remount_verified":False,"enospc":False,"source_control":"immutable-installed-image",
        "release_approved":False,"stage":"begin"}
    def provision():
        nonlocal created
        options=[
            "create","--name",name,"--network","none","--read-only",
            "--user","999:999","--cap-drop","ALL",
            "--security-opt","no-new-privileges","--pids-limit","64",
            "--memory","192m","--memory-swap","192m","--cpus","0.3",
            "--tmpfs","/tmp:rw,nosuid,nodev,noexec,size=8m,mode=1777",
            "--log-driver","local","--log-opt","max-size=1m","--log-opt","max-file=2",
            "--mount","type=bind,src="+str(mountpoint)+",dst="+BASE+"/var",
            image]
        docker(*options)
        created=True
        data=json.loads(docker("inspect",name).stdout)[0]
        if (data["HostConfig"]["NetworkMode"]!="none"
            or data["HostConfig"].get("PortBindings")
            or data["HostConfig"]["Privileged"]
            or data["HostConfig"]["ReadonlyRootfs"] is not True):
            raise RuntimeError("container isolation preflight failed")
        if len([m for m in data["Mounts"] if m["Destination"]==BASE+"/var"])!=1:
            raise RuntimeError("expected private var bind missing")
    def destroy():
        nonlocal created
        if created:
            docker("rm","-f","-v",name)
            created=False
    def start_and_probe():
        docker("start",name)
        time.sleep(wait_sec)
        code=(
           "import socket,json;"
           "s=socket.create_connection(('127.0.0.1',2222),timeout=3);"
           "s.settimeout(3);b=s.recv(100);"
           "assert b.startswith(b'SSH-2.0-');"
           "s.sendall(b'SSH-2.0-TestExt4\\r\\n');s.close();"
           "print(json.dumps({'probe':True}))")
        for _ in range(6):
            x=docker("exec",name,"/cowrie/cowrie-env/bin/python3","-c",code,check=False)
            if x.returncode==0:
                try:
                    if json.loads(x.stdout).get("probe") is True:return True
                except (ValueError,TypeError):pass
            time.sleep(2)
        return False
    try:
        report["stage"]="create_ext4"
        with disk.open("wb") as f:f.truncate(CAPACITY)
        safe_run(["mkfs.ext4","-q","-F","-m","0",str(disk)],timeout=30)
        safe_run(["mount","-t","ext4","-o","loop,nosuid,nodev,noexec",str(disk),str(mountpoint)])
        mounted=True
        for sub in ("log/cowrie","lib/cowrie","run"):
            (mountpoint/sub).mkdir(parents=True,exist_ok=True)
        for location,dirs,files in os.walk(mountpoint):
            os.chown(location,999,999)
        report["stage"]="initial_Cowrie_start"
        provision()
        if not start_and_probe():raise RuntimeError("initial SSH probe failed")
        time.sleep(1)
        log=mountpoint/"log/cowrie/cowrie.json"
        baseline,baseline_count=log_snapshot(log)
        before=assess(mountpoint)
        report["first_events"]=baseline_count
        report["initial_health_pass"]=before["passed"]
        first_preflight=inspect_local(name,str(mountpoint))
        report["initial_local_release_preflight"]=first_preflight["local_preflight_pass"]
        report["initial_local_release_issues"]=first_preflight["issues"]
        report["measured_capacity_bytes"]=before["capacity_bytes"]
        if not before["passed"] or not 8*1024*1024<=before["capacity_bytes"]<=CAPACITY:
            raise RuntimeError("not a verified bounded ext4 mount")
        # Pause the disposable Cowrie for a coherent FULL private-var snapshot.
        docker("stop","--time","5",name)
        baseline,baseline_count=log_snapshot(log)
        report["first_events"]=baseline_count
        saved_manifest=copy_verified(mountpoint,offvolume)
        report["backup_verified"]=saved_manifest==manifest(offvolume)
        docker("start",name)
        time.sleep(wait_sec)
        report["stage"]="fill_volume"
        filler=mountpoint/"synthetic-pressure.bin"
        hit=False
        try:
            with filler.open("wb",buffering=0) as f:
                for _ in range(40):f.write(b"x"*1024*1024)
        except OSError as error:
            hit=(error.errno==errno.ENOSPC)
        report["enospc"]=hit
        full=assess(mountpoint)
        report["full_health_held"]=not full["passed"] and ("FREE_SPACE_LOW" in full["issues"])
        if not hit or not report["full_health_held"]:
            raise RuntimeError("bounded filesystem did not fail closed")
        if failure_hook is not None:
            report["signed_gap_failure_hook"]=failure_hook(root,mountpoint,report) is True
            if not report["signed_gap_failure_hook"]:
                raise RuntimeError("real Cowrie gap failure hook HOLD")
        report["stage"]="stop_unmount_remount"
        docker("kill","--signal","SIGKILL",name)
        destroy()
        # Discard ONLY this disposable mounted filesystem tree.
        # The saved tree includes private Cowrie state, not only JSON logs.
        for child in list(mountpoint.iterdir()):
            if child.name=="lost+found":continue
            if child.is_symlink() or child.is_file():child.unlink()
            elif child.is_dir():shutil.rmtree(child)
            else:raise RuntimeError("unsafe test fs entry")
        shutil.copytree(offvolume,mountpoint,dirs_exist_ok=True)
        for folder,dirs,files in os.walk(mountpoint,followlinks=False):
            os.chown(folder,999,999)
            for f in files:os.chown(os.path.join(folder,f),999,999)
        report["full_var_restored"]=manifest(mountpoint)==saved_manifest
        if not report["full_var_restored"]:raise RuntimeError("full var backup differs")
        # umount flushes this specific filesystem; avoid host-wide sync.
        safe_run(["umount",str(mountpoint)],timeout=20)
        mounted=False
        safe_run(["mount","-t","ext4","-o","loop,nosuid,nodev,noexec",str(disk),str(mountpoint)])
        mounted=True
        report["remount_verified"]=manifest(mountpoint)==saved_manifest
        report["remount_health_pass"]=assess(mountpoint)["passed"]
        report["stage"]="recreate_cowrie"
        provision()
        if not start_and_probe():raise RuntimeError("recreated SSH probe failed")
        time.sleep(1)
        updated,updated_count=log_snapshot(log)
        report["second_events"]=updated_count
        report["recreate_verified"]=(updated.startswith(baseline) and updated_count>baseline_count)
        report["recovered_health_pass"]=assess(mountpoint)["passed"]
        second_preflight=inspect_local(name,str(mountpoint))
        report["recreated_local_release_preflight"]=second_preflight["local_preflight_pass"]
        report["recreated_local_release_issues"]=second_preflight["issues"]
        if recovery_hook is not None:
            report["signed_gap_recovery_hook"]=recovery_hook(root,mountpoint,report) is True
            if not report["signed_gap_recovery_hook"]:
                raise RuntimeError("real Cowrie gap recovery hook HOLD")
        if fault_hook is not None:
            # A caller-provided negative-test hook may mutate only this
            # disposable, stopped Cowrie tree. Never touch the live VPS.
            docker("stop","--time","5",name)
            report["fault_matrix_hook"]=fault_hook(root,mountpoint,report) is True
            if not report["fault_matrix_hook"]:
                raise RuntimeError("disposable Cowrie fault matrix HOLD")
        report["gap_acknowledged"]=recovery_hook is not None and report.get("signed_gap_recovery_hook") is True
        report["passed"]=all(report[k] for k in [
            "backup_verified","full_var_restored","enospc","full_health_held","remount_verified",
            "remount_health_pass","recreate_verified","recovered_health_pass",
            "initial_local_release_preflight","recreated_local_release_preflight"])
    except Exception as error:
        report["error_class"]=type(error).__name__
        report["failure_stage"]=report["stage"]
    finally:
        report["stage"]="cleanup"
        try:destroy()
        except Exception as error:report["docker_cleanup_error"]=type(error).__name__
        try:
            if mounted:
                safe_run(["umount",str(mountpoint)],timeout=20)
                mounted=False
            shutil.rmtree(root)
        except Exception as error:
            report["cleanup_error"]=type(error).__name__
        report["cleanup"]=not root.exists() and not created and not mounted
        report["passed"]=report["passed"] and report["cleanup"]
        if failure_hook is not None or recovery_hook is not None:
            report["passed"]=report["passed"] and report.get("signed_gap_failure_hook",False) and report.get("signed_gap_recovery_hook",False)
        if fault_hook is not None:
            report["passed"]=report["passed"] and report.get("fault_matrix_hook",False)
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--image-id",required=True)
    parser.add_argument("--storage-parent",default="/opt/resoarc-trapnet/staging")
    args=parser.parse_args()
    try:r=trial(args.image_id,args.storage_parent)
    except Exception as exc:
        r={"schema":"trapnet.cowrie-bounded-persistent-ext4.v040",
           "passed":False,"error_class":type(exc).__name__,"release_approved":False}
    print(json.dumps(r,sort_keys=True))
    return 0 if r["passed"] else 3
if __name__=="__main__":sys.exit(main())
