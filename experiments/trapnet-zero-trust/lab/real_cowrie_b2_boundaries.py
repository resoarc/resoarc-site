#!/usr/bin/env python3
"""B2: disposable real-Cowrie runtime + bounded storage/inode recovery audit.

This is a strict LOCAL LAB. The supplied OCI image ID must match an immutable
pinned reference. It never inspects or changes production containers, real
Cowrie logs, user data, public ports or system services.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE/"sonar"))
from cowrie_ext4_persistent_rehearsal import trial, IMAGE_DEFAULT, safe_run
from cowrie_offline_integration import docker, image_verified

MAX_B2_TEST_FILES=2048

def audit(image):
    if not sys.platform.startswith("linux") or os.geteuid()!=0:
        raise RuntimeError("authorized isolated Linux CI root required")
    if image!=IMAGE_DEFAULT:
        raise ValueError("unrecognized fixed Cowrie image ID")
    image_verified(image)
    checks={}
    def check(name,value):
        checks[name]=bool(value)
        if not value:
            raise AssertionError(name)

    def runtime_hook(name,private_var,report):
        data=json.loads(docker("inspect",name).stdout)[0]
        cfg=data["Config"]
        host=data["HostConfig"]
        checks_required={
          "immutable_image_id":data["Image"]==IMAGE_DEFAULT,
          "read_only_container_root":host["ReadonlyRootfs"] is True,
          "non_root_uid_gid":cfg.get("User")=="999:999",
          "no_privileged_mode":host["Privileged"] is False,
          "no_linux_capabilities":any(x.upper()=="ALL" for x in (host.get("CapDrop") or [])),
          "no_new_privileges":any("no-new-privileges" in x for x in (host.get("SecurityOpt") or [])),
          "pids_limit_64":host.get("PidsLimit")==64,
          "memory_limit_192MiB":host.get("Memory")==192*1024*1024,
          "swap_equals_memory_cap":host.get("MemorySwap")==192*1024*1024,
          "cpu_limit_300m":host.get("NanoCpus")==300000000,
          "network_namespace_none":host.get("NetworkMode")=="none",
          "no_published_port_bindings":not host.get("PortBindings") and
             not any(data.get("NetworkSettings",{}).get("Ports",{}).values()),
          "private_var_single_mount":len([x for x in data["Mounts"] if x["Destination"]=="/cowrie/cowrie-git/var"])==1,
          "local_rotated_docker_logs":host.get("LogConfig",{}).get("Type")=="local" and
                host.get("LogConfig",{}).get("Config",{}).get("max-size")=="1m" and
                host.get("LogConfig",{}).get("Config",{}).get("max-file")=="2",
          "tmpfs_restricted":all(v in host.get("Tmpfs",{}).get("/tmp","")
                     for v in ("nosuid","nodev","noexec","size=8m")),
        }
        for key,value in checks_required.items():
            check(key,value)
        # Actual in-container attempt, not only inspect/config.
        attempt=(
          "import json,os,stat;"
          "u=os.geteuid();"
          "cap=[s.split(':',1)[1].strip() for s in open('/proc/self/status') "
          "if s.startswith('CapEff:')][0];"
          "denied=False;"
          "\ntry:\n open('/cowrie/.b2-probe-should-not-exist','xb').close()\n"
          "except OSError:\n denied=True\n"
          "print(json.dumps({'uid':u,'caps':cap,'root_write_denied':denied,"
          "'docker_socket_absent':not os.path.exists('/var/run/docker.sock')}))"
        )
        raw=docker("exec",name,"/cowrie/cowrie-env/bin/python3","-c",attempt)
        body=json.loads(raw.stdout.strip())
        check("actual_uid_is_999",body.get("uid")==999)
        check("actual_effective_capabilities_zero",int(body.get("caps","bad"),16)==0)
        check("actual_root_write_denied",body.get("root_write_denied") is True)
        check("docker_socket_not_exposed",body.get("docker_socket_absent") is True)
        check("ext4_var_capacity_bounded",8*1024*1024<=os.statvfs(private_var).f_blocks*os.statvfs(private_var).f_frsize<=16*1024*1024)
        return True

    def storage_hook(root,private_var,report):
        disk=root/"inode-only.img"
        mount=root/"inode-only-mnt"
        mount.mkdir(mode=0o700)
        mounted=False
        try:
            with disk.open("wb") as out:
                out.truncate(16*1024*1024)
            safe_run(["mkfs.ext4","-q","-F","-N","128","-m","0",disk])
            safe_run(["mount","-t","ext4","-o","loop,nosuid,nodev,noexec",disk,mount])
            mounted=True
            stats=os.statvfs(mount)
            check("independent_inode_bounded_device",stats.f_files>0 and stats.f_files<=1024)
            old=mount/"retained-old.test-log"
            new=mount/"retained-new.test-log"
            old.write_bytes(b"synthetic-old\n")
            new.write_bytes(b"synthetic-new\n")
            before=hashlib.sha256(new.read_bytes()).hexdigest()
            exhausted=False
            file_count=0
            for n in range(MAX_B2_TEST_FILES):
                try:
                    with (mount/f"filler-{n:04d}.txt").open("xb") as f:
                        f.write(b"x")
                    file_count+=1
                except OSError as exc:
                    if exc.errno!=errno.ENOSPC:
                        raise
                    exhausted=True
                    break
            after=os.statvfs(mount)
            check("actual_inode_ENOSPC_triggered",exhausted and file_count>0)
            check("inodes_exhausted_without_filling_volume",after.f_ffree==0 and after.f_bavail>0)
            # Deletion is confined to one explicitly named synthetic
            # fixture, never globbed production logs or unknown paths.
            old.unlink()
            check("inode_recovers_after_fixture_delete",os.statvfs(mount).f_ffree>0)
            recovered=mount/"recovered-after-exhaustion.txt"
            recovered.write_bytes(b"recovered\n")
            check("log_write_recovers_after_inode_release",recovered.read_bytes()==b"recovered\n")
            check("newer_synthetic_log_integrity_preserved",hashlib.sha256(new.read_bytes()).hexdigest()==before)
            check("inode_lab_retention_does_not_clear_history",report.get("recovered_health_pass") is True and
                 report.get("enospc") is True)
            return True
        finally:
            if mounted:
                safe_run(["umount",mount])
            shutil.rmtree(mount,ignore_errors=True)
            try:
                disk.unlink(missing_ok=True)
            except OSError:
                pass

    with tempfile.TemporaryDirectory(prefix="trapnet-b2-accepted-boundaries-") as td:
        temporary=Path(td)
        temporary.chmod(0o700)
        out=trial(image,storage_parent=str(temporary),runtime_hook=runtime_hook,fault_hook=storage_hook)
        if not out.get("passed") or not out.get("cleanup"):
            return {"schema":"trapnet.real-cowrie-b2-boundaries.v059",
                    "passed":False,"failure_stage":out.get("failure_stage",out.get("stage","unknown")),
                    "error_class":out.get("error_class","unknown"),"cleanup":out.get("cleanup",False),
                    "production_modified":False,"release_approved":False}
    return {
      "schema":"trapnet.real-cowrie-b2-boundaries.v059",
      "passed":all(checks.values()),"checks_passed":len(checks),
      "runtime_enforcement_verified":True,
      "separate_inode_enospc_and_recovery":True,
      "real_Cowrie_persistent_bounded_ext4":True,
      "test_container_network":"none","public_ports":0,
      "ephemeral_containers_and_mounts_cleaned":True,
      "production_modified":False,"independent_physical_device_proven":False,
      "formal_B2_release_pass":False,"release_approved":False,
    }

def main():
    if len(sys.argv)!=2 or sys.argv[1]!=IMAGE_DEFAULT:
        print('{"schema":"trapnet.real-cowrie-b2-boundaries.v059","passed":false,"error_class":"IMAGE_PIN_REQUIRED"}')
        return 3
    try:
        result=audit(sys.argv[1])
    except (AssertionError,RuntimeError,ValueError,OSError,subprocess.SubprocessError) as exc:
        message=str(exc)
        if not (isinstance(exc,AssertionError) and len(message)<90 and message.replace("_","").isalnum()):
            message="HOLD"
        result={"schema":"trapnet.real-cowrie-b2-boundaries.v059",
                "passed":False,"error_class":type(exc).__name__,
                "failed_check":message,"release_approved":False}
    print(json.dumps(result,sort_keys=True))
    return 0 if result.get("passed") else 3

if __name__=="__main__":
    sys.exit(main())
