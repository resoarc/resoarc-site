import copy
import json
import unittest
import containment_audit as audit

def good():
    return {
      "State":{"Running":True},
      "Config":{"User":"10001:10001","Env":["PRIVATE_PASSWORD=DO_NOT_LOG","AWS_SECRET_ACCESS_KEY=fake"]},
      "HostConfig":{
        "Privileged":False,"ReadonlyRootfs":True,
        "CapDrop":["ALL"],"CapAdd":None,"SecurityOpt":["no-new-privileges:true"],
        "NetworkMode":"trapnet-internal-net","Memory":268435456,
        "NanoCpus":500000000,"PidsLimit":50,
      },
      "Mounts":[],
      "NetworkSettings":{"Networks":{"internal":{"IPAddress":"10.222.3.4"}}},
    }
class TestContainment(unittest.TestCase):
    def test_three_protected_containers(self):
        result=audit.assess({role:good() for role in audit.ROLES})
        self.assertTrue(result["passed_static_container_controls"])
        self.assertFalse(result["public_beta_ready"])
        self.assertFalse(result["real_egress_firewall_verified"])
    def test_writable_root_is_blocking(self):
        fixture=good()
        fixture["HostConfig"]["ReadonlyRootfs"]=False
        result=audit.assess({role:fixture for role in audit.ROLES})
        self.assertFalse(result["passed_static_container_controls"])
        self.assertIn("readonly_root",result["roles"]["ssh"]["failed"])
    def test_privileged_host_network_socket_and_capabilities(self):
        fixture=good();fixture["HostConfig"].update({
           "Privileged":True,"NetworkMode":"host","CapDrop":[],"CapAdd":["SYS_ADMIN"],
           "SecurityOpt":[],"Memory":0,"NanoCpus":0,"PidsLimit":0})
        fixture["Mounts"]=[{"Source":"/var/run/docker.sock","Destination":"/var/run/docker.sock"}]
        res=audit.assess({role:fixture for role in audit.ROLES})
        self.assertFalse(res["passed_static_container_controls"])
        self.assertGreaterEqual(len(res["roles"]["web"]["failed"]),8)
    def test_no_credentials_or_ips_in_output(self):
        res=audit.assess({role:good() for role in audit.ROLES})
        output=json.dumps(res)
        self.assertNotIn("DO_NOT_LOG",output)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY",output)
        self.assertNotIn("10.222.3.4",output)
    def test_missing_role_or_payload_refused(self):
        with self.assertRaises(ValueError):audit.assess({"web":good()})
        with self.assertRaises(ValueError):audit.assess({"web":good(),"ssh":good(),"edge":None})
    def test_cowrie_writable_config_volume_refused(self):
        obj=good()
        obj["Mounts"]=[
          {"Type":"volume","Destination":"/cowrie/cowrie-git/etc","RW":True},
          {"Type":"bind","Destination":"/cowrie/cowrie-git/var","RW":True}]
        x=audit.assess({role:obj for role in audit.ROLES})
        self.assertIn("writable_mounts_scoped",x["roles"]["ssh"]["failed"])
    def test_cowrie_data_mount_is_scoped(self):
        obj=good()
        obj["Mounts"]=[{"Type":"bind","Destination":"/cowrie/cowrie-git/var","RW":True}]
        x=audit.assess({"ssh":obj,"web":good(),"edge":good()})
        self.assertTrue(x["roles"]["ssh"]["checks"]["writable_mounts_scoped"])
    def test_web_writable_app_rejected(self):
        obj=good()
        obj["Mounts"]=[{"Type":"bind","Destination":"/app","RW":True}]
        x=audit.assess({"web":obj,"ssh":good(),"edge":good()})
        self.assertIn("writable_mounts_scoped",x["roles"]["web"]["failed"])
    def test_bounded_tmpfs_for_web(self):
        fixture=good()
        fixture["HostConfig"]["Tmpfs"]={"/tmp":"rw,noexec,nosuid,nodev,size=16m,mode=1777"}
        self.assertTrue(audit.audit_one(fixture,"web")["tmpfs_scoped"])
    def test_unexpected_tmpfs_path_refused(self):
        fixture=good()
        fixture["HostConfig"]["Tmpfs"]={"/etc":"rw,noexec,nosuid,nodev,size=8m"}
        self.assertFalse(audit.audit_one(fixture,"web")["tmpfs_scoped"])
    def test_tmpfs_unbounded_or_executable_refused(self):
        fixture=good()
        for config in ("rw,nosuid,nodev,size=16m","rw,noexec,nosuid,nodev",
                       "rw,noexec,nosuid,nodev,size=400m",
                       "rw,noexec,nosuid,nodev,size=1m,exec"):
            fixture["HostConfig"]["Tmpfs"]={"/tmp":config}
            self.assertFalse(audit.audit_one(fixture,"web")["tmpfs_scoped"])
    def test_shared_pid_ipc_refused(self):
        fixture=good();fixture["HostConfig"]["PidMode"]="host"
        self.assertFalse(audit.audit_one(fixture,"web")["namespaces_and_devices_private"])
        fixture["HostConfig"]["PidMode"]=""
        fixture["HostConfig"]["IpcMode"]="host"
        self.assertFalse(audit.audit_one(fixture,"web")["namespaces_and_devices_private"])
    def test_added_devices_refused(self):
        fixture=good()
        fixture["HostConfig"]["Devices"]=[{"PathOnHost":"/dev/fuse"}]
        self.assertFalse(audit.audit_one(fixture,"web")["namespaces_and_devices_private"])
    def test_inherited_volumes_refused(self):
        fixture=good();fixture["HostConfig"]["VolumesFrom"]=["other:rw"]
        self.assertFalse(audit.audit_one(fixture,"web")["namespaces_and_devices_private"])
    def test_default_private_namespaces(self):
        fixture=good()
        fixture["HostConfig"]["IpcMode"]="private"
        self.assertTrue(audit.audit_one(fixture,"web")["namespaces_and_devices_private"])
    def test_unexpected_readonly_destination_rejected(self):
        obj=good()
        obj["Mounts"]=[{"Type":"bind","Destination":"/etc/hosts","RW":False}]
        self.assertFalse(audit.audit_one(obj,"web")["writable_mounts_scoped"])
    def test_known_readonly_web_destination_accepted(self):
        obj=good()
        obj["Mounts"]=[{"Type":"bind","Destination":"/app","RW":False}]
        self.assertTrue(audit.audit_one(obj,"web")["writable_mounts_scoped"])
    def test_known_readonly_edge_destination_accepted(self):
        obj=good()
        obj["Mounts"]=[{"Type":"bind","Destination":"/usr/local/etc/haproxy/haproxy.cfg","RW":False}]
        self.assertTrue(audit.audit_one(obj,"edge")["writable_mounts_scoped"])
    def test_cowrie_readonly_config_only(self):
        obj=good()
        obj["Mounts"]=[
            {"Type":"bind","Destination":"/cowrie/cowrie-git/etc/cowrie.cfg","RW":False},
            {"Type":"bind","Destination":"/cowrie/cowrie-git/var","RW":True}]
        self.assertTrue(audit.audit_one(obj,"ssh")["writable_mounts_scoped"])
        obj["Mounts"][0]["RW"]=True
        self.assertFalse(audit.audit_one(obj,"ssh")["writable_mounts_scoped"])
    def test_readonly_volume_refused(self):
        obj=good()
        obj["Mounts"]=[{"Type":"volume","Destination":"/app","RW":False}]
        self.assertFalse(audit.audit_one(obj,"web")["writable_mounts_scoped"])
    def test_readonly_socket_refused(self):
        obj=good()
        obj["Mounts"]=[{"Type":"bind","Source":"/var/run/docker.sock",
                        "Destination":"/var/run/docker.sock","RW":False}]
        self.assertFalse(audit.audit_one(obj,"web")["writable_mounts_scoped"])
    def test_host_source_review_not_claimed(self):
        obj=good()
        obj["Mounts"]=[{"Type":"bind","Destination":"/app","RW":False}]
        result=audit.assess({"web":obj,"ssh":good(),"edge":good()})
        self.assertTrue(result["roles"]["web"]["checks"]["writable_mounts_scoped"])
        self.assertFalse(result["mount_source_ownership_and_content_verified"])
        self.assertFalse(result["image_declared_volume_override_verified"])
    def test_nonroot_default_not_sufficient(self):
        fixture=good();fixture["Config"]["User"]=""
        res=audit.assess({role:fixture for role in audit.ROLES})
        self.assertFalse(res["passed_static_container_controls"])
        self.assertFalse(res["roles"]["web"]["checks"]["nonroot_user"])
if __name__=="__main__":unittest.main()