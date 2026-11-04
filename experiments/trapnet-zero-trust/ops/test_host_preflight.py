#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic, offline regression tests for the read-only Cowrie preflight."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("host_preflight", HERE / "host_preflight.py")
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)


def good_inspect():
    return {
        "Name": "/trapnet-cowrie", "Id": "a" * 64,
        "State": {"Running": True},
        "NetworkSettings": {"Networks": {"trapnet-sensor-strict": {}}},
        "Config": {"User": "999:999", "Env": ["SECRET=never_echo_this"]},
        "HostConfig": {
            "ReadonlyRootfs": True, "Privileged": False, "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"], "Memory": 192 * 1024 * 1024,
            "MemorySwap": 192 * 1024 * 1024, "NanoCpus": 300000000,
            "PidsLimit": 64, "NetworkMode": "trapnet-sensor-strict",
            "PortBindings": {}, "PublishAllPorts": False,
            "LogConfig": {"Type": "local", "Config": {"max-size": "5m", "max-file": "3"}},
        },
        "Mounts": [{"Type": "bind", "Source": "/tmp/var-secure-fixture",
                    "Destination": "/cowrie/var", "RW": True}],
    }


def good_storage():
    return {"directory_owner_only": True, "files_owner_only_regular_unlinked": True,
            "owners_match_service": True, "separate_root_device": True, "file_count": 3}


class PreflightTests(unittest.TestCase):
    def report(self, obj=None, storage=None):
        return pf.assess(obj if obj is not None else good_inspect(),
                         storage if storage is not None else good_storage(),
                         "trapnet-sensor-strict")

    def test_valid_synthetic_profile_is_not_release_approval(self):
        report = self.report()
        self.assertEqual(report["profile_result"], "PASS")
        self.assertEqual(report["formal_release"], "HOLD")
        self.assertFalse(report["quota_verified"])
        self.assertFalse(report["retention_verified"])
        self.assertFalse(report["independent_review_verified"])

    def test_writable_root_rejected(self):
        x = good_inspect(); x["HostConfig"]["ReadonlyRootfs"] = False
        self.assertIn("rootfs_readonly", self.report(x)["finding_codes"])

    def test_privileged_rejected(self):
        x = good_inspect(); x["HostConfig"]["Privileged"] = True
        self.assertIn("not_privileged", self.report(x)["finding_codes"])

    def test_root_user_rejected(self):
        for user in ("", "0:0", "999", "root", "999:0", "0:999"):
            x = good_inspect(); x["Config"]["User"] = user
            with self.subTest(user=user):
                self.assertIn("nonroot_uid_gid", self.report(x)["finding_codes"])

    def test_capabilities_rejected(self):
        x = good_inspect(); x["HostConfig"]["CapDrop"] = []
        self.assertIn("capabilities_dropped", self.report(x)["finding_codes"])

    def test_no_new_privileges_required(self):
        x = good_inspect(); x["HostConfig"]["SecurityOpt"] = []
        self.assertIn("no_new_privileges", self.report(x)["finding_codes"])

    def test_missing_memory_limit_rejected(self):
        x = good_inspect(); x["HostConfig"]["Memory"] = 0
        self.assertIn("memory_bounded", self.report(x)["finding_codes"])

    def test_excess_memory_limit_rejected(self):
        x = good_inspect(); x["HostConfig"]["Memory"] = 2 ** 40
        self.assertIn("memory_bounded", self.report(x)["finding_codes"])

    def test_memory_limit_bool_not_int(self):
        x = good_inspect(); x["HostConfig"]["Memory"] = True
        self.assertIn("memory_bounded", self.report(x)["finding_codes"])

    def test_swap_unbounded_rejected(self):
        x = good_inspect(); x["HostConfig"]["MemorySwap"] = 0
        self.assertIn("swap_bounded", self.report(x)["finding_codes"])

    def test_cpu_pid_bounds(self):
        x = good_inspect(); x["HostConfig"]["NanoCpus"] = 500000000
        x["HostConfig"]["PidsLimit"] = 0
        report = self.report(x)
        self.assertIn("cpu_bounded", report["finding_codes"])
        self.assertIn("pids_bounded", report["finding_codes"])

    def test_host_network_rejected(self):
        x = good_inspect(); x["HostConfig"]["NetworkMode"] = "host"
        self.assertIn("expected_isolated_network", self.report(x)["finding_codes"])

    def test_extra_connected_network_rejected(self):
        x = good_inspect()
        x["NetworkSettings"]["Networks"]["bridge"] = {}
        self.assertIn("no_extra_networks", self.report(x)["finding_codes"])

    def test_unexpected_tmpfs_mount_rejected(self):
        x = good_inspect()
        x["Mounts"].append({"Type": "tmpfs", "Destination": "/etc", "RW": True})
        self.assertIn("no_unexpected_mount_types", self.report(x)["finding_codes"])

    def test_unexpected_network_rejected(self):
        x = good_inspect(); x["HostConfig"]["NetworkMode"] = "other"
        self.assertIn("expected_isolated_network", self.report(x)["finding_codes"])

    def test_host_ports_rejected(self):
        x = good_inspect(); x["HostConfig"]["PortBindings"] = {"22/tcp": [{"HostPort": "2222"}]}
        self.assertIn("no_host_ports", self.report(x)["finding_codes"])

    def test_publish_all_rejected(self):
        x = good_inspect(); x["HostConfig"]["PublishAllPorts"] = True
        self.assertIn("no_host_ports", self.report(x)["finding_codes"])

    def test_docker_socket_mount_rejected(self):
        x = good_inspect()
        x["Mounts"].append({"Type": "bind", "Source": "/var/run/docker.sock",
                            "Destination": "/var/run/docker.sock", "RW": True})
        report = self.report(x)
        self.assertIn("no_docker_socket", report["finding_codes"])
        self.assertIn("single_private_var_bind", report["finding_codes"])

    def test_extra_mount_rejected(self):
        x = good_inspect()
        x["Mounts"].append({"Type": "bind", "Source": "/tmp/extra",
                            "Destination": "/etc/ssh", "RW": False})
        self.assertIn("single_private_var_bind", self.report(x)["finding_codes"])

    def test_private_mount_must_be_rw(self):
        x = good_inspect(); x["Mounts"][0]["RW"] = False
        self.assertIn("single_private_var_bind", self.report(x)["finding_codes"])

    def test_no_docker_local_log_caps_rejected(self):
        x = good_inspect(); x["HostConfig"]["LogConfig"]["Config"] = {}
        self.assertIn("bounded_stdout_driver", self.report(x)["finding_codes"])

    def test_wrong_container_identity_rejected(self):
        x = good_inspect(); x["Name"] = "/unrelated"
        self.assertIn("container_identity", self.report(x)["finding_codes"])

    def test_missing_or_malformed_identity_rejected(self):
        x = good_inspect(); x["Id"] = "a" * 63
        self.assertIn("container_identity", self.report(x)["finding_codes"])

    def test_wrong_types_fail_closed(self):
        x = good_inspect(); x["HostConfig"] = "forged"
        self.assertEqual(self.report(x)["profile_result"], "HOLD")

    def test_owner_mismatch_rejected(self):
        x = good_storage(); x["owners_match_service"] = False
        self.assertIn("owners_match_service", self.report(storage=x)["finding_codes"])

    def test_absurd_stdout_limits_rejected(self):
        x = good_inspect()
        x["HostConfig"]["LogConfig"]["Config"] = {"max-size": "999999m", "max-file": "999"}
        self.assertIn("bounded_stdout_driver", self.report(x)["finding_codes"])

    def test_not_running_rejected(self):
        x = good_inspect(); x["State"]["Running"] = False
        self.assertIn("container_running", self.report(x)["finding_codes"])

    def test_world_readable_log_file_rejected(self):
        x = good_storage(); x["files_owner_only_regular_unlinked"] = False
        self.assertIn("files_owner_only_regular_unlinked", self.report(storage=x)["finding_codes"])

    def test_directory_permission_rejected(self):
        x = good_storage(); x["directory_owner_only"] = False
        self.assertIn("directory_owner_only", self.report(storage=x)["finding_codes"])

    def test_same_root_device_rejected(self):
        x = good_storage(); x["separate_root_device"] = False
        self.assertIn("separate_root_device", self.report(storage=x)["finding_codes"])

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(pf.UnsafeInput):
            pf.parse_inspect(b'{"HostConfig":{},"HostConfig":{"Privileged":true}}')

    def test_multiple_inspect_objects_rejected(self):
        with self.assertRaises(pf.UnsafeInput):
            pf.parse_inspect(b'[{},{}]')

    def test_oversize_input_rejected(self):
        with self.assertRaises(pf.UnsafeInput):
            pf.parse_inspect(b"x" * (pf.MAX_INSPECT_BYTES + 1))

    def test_output_never_echoes_inspect_secret(self):
        result = json.dumps(self.report(good_inspect()))
        self.assertNotIn("never_echo_this", result)
        self.assertNotIn("/tmp/var-secure-fixture", result)
        self.assertNotIn("HostPort", result)

    @unittest.skipUnless(os.name == "posix", "Linux host permission test")
    def test_real_metadata_same_device_and_modes(self):
        with tempfile.TemporaryDirectory(prefix="trapnet-preflight-") as root:
            base = Path(root)
            mount = base / "var"
            logs = mount / "log"
            logs.mkdir(parents=True, mode=0o700)
            logs.chmod(0o700)
            (logs / "event.json").write_text("synthetic only")
            (logs / "event.json").chmod(0o600)
            data = pf.collect_log_metadata(logs, str(mount), expected_uid=os.getuid())
            self.assertTrue(data["directory_owner_only"])
            self.assertTrue(data["files_owner_only_regular_unlinked"])
            self.assertFalse(data["separate_root_device"])
            (logs / "event.json").chmod(0o664)
            data2 = pf.collect_log_metadata(logs, str(mount), expected_uid=os.getuid())
            self.assertFalse(data2["files_owner_only_regular_unlinked"])

    @unittest.skipUnless(os.name == "posix", "Linux host permission test")
    def test_symlink_log_entry_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="trapnet-preflight-") as root:
            base = Path(root)
            logs = base / "log"
            logs.mkdir(mode=0o700)
            target = base / "target"
            target.write_text("synthetic")
            (logs / "link").symlink_to(target)
            data = pf.collect_log_metadata(logs, str(base), expected_uid=os.getuid())
            self.assertFalse(data["files_owner_only_regular_unlinked"])

    @unittest.skipUnless(os.name == "posix", "Linux host permission test")
    def test_symlink_directory_rejected(self):
        with tempfile.TemporaryDirectory(prefix="trapnet-preflight-") as root:
            base = Path(root)
            d = base / "real"
            d.mkdir()
            linked = base / "alias"
            linked.symlink_to(d)
            with self.assertRaises(pf.UnsafeInput):
                pf.collect_log_metadata(linked, str(base))


if __name__ == "__main__":
    unittest.main()
