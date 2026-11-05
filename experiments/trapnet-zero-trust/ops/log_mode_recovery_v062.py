#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed Cowrie raw-log mode normalization (not retention or release approval).

The only automatic mutation allowed is fchmod(0600) for an ordinary, single-link,
service-owned active cowrie.json with exactly mode 0664, inside a service-owned
0700 directory on an already-mounted non-root filesystem. No log bytes are read.
Unrecognized changes remain HOLD.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

SCHEMA = "trapnet.cowrie.log-mode-recovery.v062"
EXPECTED_UID = 999
ACTIVE_NAME = "cowrie.json"
REPAIRABLE_MODE = 0o664
SAFE_MODE = 0o600
MAX_FILES = 4096


class UnsafeMetadata(Exception):
    pass


def authorize_active_repair(name, mode, uid, nlink, is_regular, expected_uid):
    """Pure policy: never repair other entries, modes, owners, or links."""
    return (
        name == ACTIVE_NAME
        and type(mode) is int and mode == REPAIRABLE_MODE
        and type(uid) is int and uid == expected_uid
        and nlink == 1
        and is_regular is True
    )


def _trusted_log_directory(path: Path, uid: int):
    if not path.is_absolute():
        raise UnsafeMetadata("non_absolute_directory")
    cur = path
    while True:
        s = os.lstat(cur)
        if stat.S_ISLNK(s.st_mode):
            raise UnsafeMetadata("symlink_directory_component")
        if cur.parent == cur:
            break
        cur = cur.parent
    s = os.lstat(path)
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != uid or stat.S_IMODE(s.st_mode) != 0o700:
        raise UnsafeMetadata("untrusted_raw_log_directory")


def inspect_and_normalize(log_dir: Path, expected_uid: int, repair: bool):
    _trusted_log_directory(log_dir, expected_uid)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(log_dir, directory_flags)
    repaired = 0
    repairable = 0
    checked = 0
    try:
        with os.scandir(fd) as iterator:
            for entry in iterator:
                checked += 1
                if checked > MAX_FILES:
                    raise UnsafeMetadata("file_limit_exceeded")
                s = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                is_regular = stat.S_ISREG(s.st_mode)
                if not is_regular or s.st_nlink != 1 or s.st_uid != expected_uid:
                    raise UnsafeMetadata("unexpected_type_owner_or_link")
                mode = stat.S_IMODE(s.st_mode)
                if mode == SAFE_MODE:
                    continue
                if not authorize_active_repair(entry.name, mode, s.st_uid,
                                               s.st_nlink, is_regular, expected_uid):
                    raise UnsafeMetadata("unrecognized_log_mode")
                repairable += 1
                if not repair:
                    continue
                file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                file_flags |= getattr(os, "O_CLOEXEC", 0)
                file_fd = os.open(entry.name, file_flags, dir_fd=fd)
                try:
                    pinned = os.fstat(file_fd)
                    if (pinned.st_ino, pinned.st_dev) != (s.st_ino, s.st_dev):
                        raise UnsafeMetadata("file_raced_before_repair")
                    if not authorize_active_repair(entry.name, stat.S_IMODE(pinned.st_mode),
                                                   pinned.st_uid, pinned.st_nlink,
                                                   stat.S_ISREG(pinned.st_mode), expected_uid):
                        raise UnsafeMetadata("file_changed_before_repair")
                    os.fchmod(file_fd, SAFE_MODE)
                    after = os.fstat(file_fd)
                    if stat.S_IMODE(after.st_mode) != SAFE_MODE:
                        raise UnsafeMetadata("repair_not_effective")
                    repaired += 1
                finally:
                    os.close(file_fd)
        if checked == 0:
            raise UnsafeMetadata("missing_raw_logs")
    finally:
        os.close(fd)
    return {"checked": checked, "repairable": repairable, "repaired": repaired}


def verify_bounded_mount(volume: Path, root: Path = Path("/")):
    if not volume.is_absolute() or not os.path.ismount(volume):
        raise UnsafeMetadata("bounded_mount_missing")
    if os.stat(volume).st_dev == os.stat(root).st_dev:
        raise UnsafeMetadata("raw_logs_share_root_device")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", default="/opt/resoarc-trapnet/var/log/cowrie")
    parser.add_argument("--bounded-mount", default="/opt/resoarc-trapnet/var")
    parser.add_argument("--service-uid", type=int, default=EXPECTED_UID)
    parser.add_argument("--repair-known-mode", action="store_true", default=False)
    args = parser.parse_args(argv)
    try:
        if os.name != "posix" or args.service_uid <= 0:
            raise UnsafeMetadata("unsupported_os_or_uid")
        verify_bounded_mount(Path(args.bounded_mount))
        summary = inspect_and_normalize(Path(args.log_dir), args.service_uid, args.repair_known_mode)
        report = {"schema": SCHEMA, "result": "PASS", "formal_release": "HOLD",
                  "files_checked": summary["checked"], "known_mode_anomalies": summary["repairable"],
                  "files_repaired": summary["repaired"], "raw_data_read": False}
    except (UnsafeMetadata, OSError, ValueError, TypeError):
        report = {"schema": SCHEMA, "result": "HOLD", "formal_release": "HOLD",
                  "finding_codes": ["log_mode_metadata_untrusted_or_repair_failed"]}
    if report["result"] == "PASS" and not args.repair_known_mode and report["known_mode_anomalies"]:
        report["result"] = "HOLD"
        report["finding_codes"] = ["known_active_log_mode_repair_required"]
    if report["result"] == "PASS" and report.get("files_repaired", 0):
        # Only emit a constant metadata-only incident marker; never raw log contents.
        try:
            import subprocess
            subprocess.run(["logger", "-t", "trapnet-cowrie-v062",
                            "repaired_known_active_log_mode_0664_to_0600"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=2, check=False)
        except (OSError, subprocess.SubprocessError):
            pass
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
