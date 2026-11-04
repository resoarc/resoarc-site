#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed, read-only metadata preflight for an operator-owned Cowrie host.

Not a deployment tool, production compliance assessment, or release authorization.
No log contents, filenames, IPs, paths or environment variables enter its output.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SCHEMA = "trapnet.cowrie.readonly-preflight.v061"
MAX_INSPECT_BYTES = 2_000_000
MAX_ENTRIES = 2048
MAX_MEMORY = 192 * 1024 * 1024
MAX_CPU = 300_000_000
MAX_PIDS = 64
CONTAINER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class UnsafeInput(Exception):
    """Fail closed without exposing untrusted text."""


def _unique_pairs(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise UnsafeInput("duplicate_json_key")
        result[key] = val
    return result


def parse_inspect(raw: bytes):
    if len(raw) > MAX_INSPECT_BYTES:
        raise UnsafeInput("inspect_too_large")
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (ValueError, UnicodeError) as exc:
        raise UnsafeInput("invalid_inspect_json") from exc
    if isinstance(obj, list):
        if len(obj) != 1:
            raise UnsafeInput("unexpected_inspect_count")
        obj = obj[0]
    if not isinstance(obj, dict):
        raise UnsafeInput("unexpected_inspect_type")
    return obj


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _bounded_positive(value, limit):
    return type(value) is int and 0 < value <= limit


def assess_runtime(inspect, expected_network: str, expected_mount: str = "/cowrie/var", expected_container: str = "trapnet-cowrie"):
    hc = _dict(inspect.get("HostConfig"))
    cfg = _dict(inspect.get("Config"))
    state = _dict(inspect.get("State"))
    memory = hc.get("Memory")
    mounts = _list(inspect.get("Mounts"))
    user = cfg.get("User")
    user_ok = isinstance(user, str) and bool(re.fullmatch(r"[1-9]\d*:[1-9]\d*", user))
    security = _list(hc.get("SecurityOpt"))
    capdrop = _list(hc.get("CapDrop"))
    portbindings = hc.get("PortBindings")
    # No host bind except precisely one private-var mount. Tmpfs is not a host bind.
    binds = [m for m in mounts if isinstance(m, dict) and m.get("Type") in ("bind", "volume")]
    varmount = [m for m in binds if m.get("Destination") == expected_mount]
    no_socket = all(
        isinstance(m, dict)
        and "docker.sock" not in str(m.get("Destination", ""))
        and "docker.sock" not in str(m.get("Source", ""))
        for m in mounts
    )
    mount_ok = (
        len(binds) == 1 and len(varmount) == 1 and
        varmount[0].get("Type") == "bind" and
        varmount[0].get("RW") is True and
        isinstance(varmount[0].get("Source"), str) and
        os.path.isabs(varmount[0]["Source"]) and
        varmount[0]["Source"] != "/"
    )
    approved_mounts = all(
        isinstance(m, dict)
        and ((m.get("Type") == "bind" and m.get("Destination") == expected_mount)
             or (m.get("Type") == "tmpfs" and m.get("Destination") == "/tmp"))
        for m in mounts
    )
    networks = _dict(_dict(inspect.get("NetworkSettings")).get("Networks"))
    opts = _dict(_dict(hc.get("LogConfig")).get("Config"))
    check = {
        "container_identity": (
            inspect.get("Name") == "/" + expected_container
            and isinstance(inspect.get("Id"), str)
            and bool(re.fullmatch(r"[0-9a-f]{64}", inspect["Id"]))
        ),
        "container_running": state.get("Running") is True,
        "rootfs_readonly": hc.get("ReadonlyRootfs") is True,
        "nonroot_uid_gid": user_ok,
        "not_privileged": hc.get("Privileged") is False,
        "capabilities_dropped": "ALL" in capdrop,
        "no_new_privileges": any(s in ("no-new-privileges", "no-new-privileges:true") for s in security),
        "memory_bounded": _bounded_positive(memory, MAX_MEMORY),
        "swap_bounded": _bounded_positive(memory, MAX_MEMORY) and hc.get("MemorySwap") == memory,
        "cpu_bounded": _bounded_positive(hc.get("NanoCpus"), MAX_CPU),
        "pids_bounded": _bounded_positive(hc.get("PidsLimit"), MAX_PIDS),
        "expected_isolated_network": (
            expected_network not in ("host", "bridge", "none", "default") and
            hc.get("NetworkMode") == expected_network
        ),
        "no_extra_networks": set(networks) == {expected_network},
        "no_host_ports": portbindings in (None, {}) and hc.get("PublishAllPorts") is False,
        "no_docker_socket": no_socket,
        "single_private_var_bind": mount_ok,
        "no_unexpected_mount_types": approved_mounts,
        "bounded_stdout_driver": (
            _dict(hc.get("LogConfig")).get("Type") == "local"
            and isinstance(opts.get("max-size"), str)
            and isinstance(opts.get("max-file"), str)
            and bool(re.fullmatch(r"[1-9]\d*[kKmM]", opts["max-size"]))
            and bool(re.fullmatch(r"[1-9]\d*", opts["max-file"]))
            and int(opts["max-size"][:-1]) * (
                1024 if opts["max-size"][-1:].lower() == "k" else 1024 * 1024
            ) <= 20 * 1024 * 1024
            and int(opts["max-file"]) <= 5
        ),
    }
    source = varmount[0]["Source"] if mount_ok else None
    return check, source, int(user.split(":")[0]) if user_ok else None


def _no_symlink_components(path: Path):
    p = path.absolute()
    while True:
        if stat.S_ISLNK(os.lstat(p).st_mode):
            return False
        if p.parent == p:
            return True
        p = p.parent


def collect_log_metadata(log_dir: Path, mount_source: str | None, root_dir: Path = Path("/"), expected_uid: int | None = None):
    """Inspect names only as opaque directory entries: never read raw log bytes."""
    if not log_dir.is_absolute() or mount_source is None:
        raise UnsafeInput("missing_log_directory_or_mount")
    if not _no_symlink_components(log_dir) or not _no_symlink_components(Path(mount_source)):
        raise UnsafeInput("symlink_in_path")
    directory = os.lstat(log_dir)
    if not stat.S_ISDIR(directory.st_mode):
        raise UnsafeInput("log_directory_not_directory")
    path_real = os.path.realpath(str(log_dir))
    source_real = os.path.realpath(mount_source)
    if os.path.commonpath([path_real, source_real]) != source_real:
        raise UnsafeInput("log_directory_not_inside_mount")
    count = 0
    all_files_safe = True
    owners_match = expected_uid is not None and directory.st_uid == expected_uid
    with os.scandir(log_dir) as entries:
        for entry in entries:
            count += 1
            if count > MAX_ENTRIES:
                raise UnsafeInput("too_many_log_entries")
            item = entry.stat(follow_symlinks=False)
            if (not stat.S_ISREG(item.st_mode) or stat.S_IMODE(item.st_mode) != 0o600
                    or item.st_nlink != 1):
                all_files_safe = False
            if item.st_uid != expected_uid:
                owners_match = False
    return {
        "directory_owner_only": stat.S_IMODE(directory.st_mode) == 0o700,
        "files_owner_only_regular_unlinked": all_files_safe and count > 0,
        "owners_match_service": owners_match and count > 0,
        "separate_root_device": directory.st_dev != os.stat(root_dir).st_dev,
        "file_count": count,
    }


def assess(inspect, storage, expected_network: str, expected_mount: str = "/cowrie/var", expected_container: str = "trapnet-cowrie"):
    runtime, _, _ = assess_runtime(inspect, expected_network, expected_mount, expected_container)
    if not isinstance(storage, dict):
        storage = {}
    checks = dict(runtime)
    checks.update({
        "directory_owner_only": storage.get("directory_owner_only") is True,
        "files_owner_only_regular_unlinked": storage.get("files_owner_only_regular_unlinked") is True,
        "owners_match_service": storage.get("owners_match_service") is True,
        "separate_root_device": storage.get("separate_root_device") is True,
    })
    failing = sorted(key for key, ok in checks.items() if not ok)
    return {
        "schema": SCHEMA,
        "profile_result": "PASS" if not failing else "HOLD",
        "formal_release": "HOLD",
        "quota_verified": False,
        "retention_verified": False,
        "independent_review_verified": False,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failing),
        "finding_codes": failing,
        "observed_file_count": storage.get("file_count") if type(storage.get("file_count")) is int else None,
        "notice": "Metadata snapshot only; physical quota, backups, production behavior and approval NOT proven",
    }


def _inspect_bytes(args):
    if args.inspect_file:
        file = Path(args.inspect_file)
        if not file.is_file() or file.is_symlink() or file.stat().st_size > MAX_INSPECT_BYTES:
            raise UnsafeInput("unsafe_inspect_file")
        return file.read_bytes()
    if not CONTAINER_NAME.fullmatch(args.container):
        raise UnsafeInput("invalid_container_name")
    # Docker inspect is a read-only local metadata query. Never use exec, logs or restart.
    try:
        p = subprocess.run(["docker", "inspect", args.container], shell=False,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=12, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise UnsafeInput("docker_inspect_failed") from exc
    return p.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--inspect-file", help="Private Docker inspect JSON; never upload this file")
    source.add_argument("--container", help="Existing container to inspect locally (read only)")
    parser.add_argument("--log-dir", required=True, help="Existing raw log directory; metadata only")
    parser.add_argument("--expected-network", required=True, help="Explicit isolated Docker network name")
    parser.add_argument("--expected-container", required=True, help="Expected exact container name, not ID")
    parser.add_argument("--expected-mount", default="/cowrie/var")
    args = parser.parse_args(argv)
    try:
        if os.name != "posix":
            raise UnsafeInput("linux_host_required")
        obj = parse_inspect(_inspect_bytes(args))
        _, mount_source, uid = assess_runtime(obj, args.expected_network, args.expected_mount, args.expected_container)
        storage = collect_log_metadata(Path(args.log_dir), mount_source, expected_uid=uid)
        report = assess(obj, storage, args.expected_network, args.expected_mount, args.expected_container)
    except (UnsafeInput, OSError, ValueError, TypeError):
        report = {"schema": SCHEMA, "profile_result": "HOLD", "formal_release": "HOLD",
                  "finding_codes": ["preflight_input_or_collection_failed"]}
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0 if report.get("profile_result") == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
