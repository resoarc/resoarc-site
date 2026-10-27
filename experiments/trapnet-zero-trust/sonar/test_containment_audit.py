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
    def test_nonroot_default_not_sufficient(self):
        fixture=good();fixture["Config"]["User"]=""
        res=audit.assess({role:fixture for role in audit.ROLES})
        self.assertFalse(res["passed_static_container_controls"])
        self.assertFalse(res["roles"]["web"]["checks"]["nonroot_user"])
if __name__=="__main__":unittest.main()
