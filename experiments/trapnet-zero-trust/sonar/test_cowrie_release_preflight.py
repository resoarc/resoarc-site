#!/usr/bin/env python3
"""Local, no-network regression for release readiness conditions."""
import json
import unittest
from unittest.mock import patch
import cowrie_release_preflight as r

DIGEST="sha256:"+"a"*64

def config():
 return {
  "Image":DIGEST,
  "State":{"Running":True},
  "Config":{"User":"999:999","Image":DIGEST},
  "Mounts":[{"Destination":"/cowrie/cowrie-git/var","Type":"bind"}],
  "HostConfig":{
    "NetworkMode":"trapnet-sensor-strict",
    "Privileged":False,"ReadonlyRootfs":True,
    "PortBindings":None,"CapDrop":["ALL"],"SecurityOpt":["no-new-privileges:true"],
    "Memory":180*1024*1024,"NanoCpus":300000000,"PidsLimit":64,
    "LogConfig":{"Type":"local","Config":{"max-size":"1m","max-file":"2"}}
  }
}

def healthy():return {"passed":True,"capacity_bytes":16000000}

class ReadonlyPreflight(unittest.TestCase):
 def check(self,c=None,h=None,internal=True):
  return r.assess_config(config() if c is None else c,internal,healthy() if h is None else h)
 def test_valid_bounded_local_does_not_approve_public(self):
  x=self.check()
  self.assertTrue(x["local_preflight_pass"])
  self.assertFalse(x["production_release_approved"])
  self.assertFalse(x["feed_publishable"])
 def test_log_unbounded_holds(self):
  x=self.check(h={"passed":False})
  self.assertIn("PERSISTENT_LOG_CAPACITY_NOT_PROVEN",x["issues"])
 def test_no_internal_network_holds(self):
  self.assertIn("NETWORK_NOT_INTERNAL",self.check(internal=False)["issues"])
 def test_host_network_holds(self):
  c=config();c["HostConfig"]["NetworkMode"]="host"
  self.assertIn("NETWORK_ISOLATION_NOT_PROVEN",self.check(c)["issues"])
 def test_privileged_holds(self):
  c=config();c["HostConfig"]["Privileged"]=True
  self.assertFalse(self.check(c)["local_preflight_pass"])
 def test_root_user_holds(self):
  c=config();c["Config"]["User"]="0:0"
  self.assertIn("ROOT_USER_NOT_EXCLUDED",self.check(c)["issues"])
 def test_unpinned_declarative_image_holds(self):
  c=config();c["Config"]["Image"]="cowrie/cowrie:latest"
  self.assertIn("IMMUTABLE_DEPLOYMENT_REFERENCE_NOT_PROVEN",self.check(c)["issues"])
 def test_immutable_repository_digest_accepted(self):
  c=config();c["Config"]["Image"]="cowrie/cowrie@"+DIGEST
  self.assertTrue(self.check(c)["local_preflight_pass"])
 def test_mutable_repository_tag_refused(self):
  c=config();c["Config"]["Image"]="cowrie/cowrie:latest"
  self.assertIn("IMMUTABLE_DEPLOYMENT_REFERENCE_NOT_PROVEN",self.check(c)["issues"])
 def test_writable_root_holds(self):
  c=config();c["HostConfig"]["ReadonlyRootfs"]=False
  self.assertIn("WRITABLE_CONTAINER_ROOT",self.check(c)["issues"])
 def test_docker_sock_holds(self):
  c=config();c["Mounts"].append({"Destination":"/var/run/docker.sock"})
  self.assertIn("DOCKER_SOCKET_MOUNT",self.check(c)["issues"])
 def test_missing_limits_hold(self):
  c=config();c["HostConfig"]["Memory"]=0;c["HostConfig"]["NanoCpus"]=0;c["HostConfig"]["PidsLimit"]=0
  issues=self.check(c)["issues"]
  for name in ("MEMORY_NOT_BOUNDED","CPU_NOT_BOUNDED","PIDS_NOT_BOUNDED"):self.assertIn(name,issues)
 def test_no_published_ports(self):
  c=config();c["HostConfig"]["PortBindings"]={"2222/tcp":[{"HostPort":"2222"}]}
  self.assertIn("PORTS_PUBLISHED",self.check(c)["issues"])
 def test_missing_log_rotation_holds(self):
  c=config();c["HostConfig"]["LogConfig"]["Config"]={}
  self.assertIn("DOCKER_LOG_ROTATION_NOT_PROVEN",self.check(c)["issues"])
 def test_docker_no_new_privileges_short_form_accepted(self):
  c=config();c["HostConfig"]["SecurityOpt"]=["no-new-privileges"]
  self.assertTrue(self.check(c)["local_preflight_pass"])
 def test_explicit_disabled_privilege_protection_refused(self):
  c=config();c["HostConfig"]["SecurityOpt"]=["no-new-privileges:false"]
  self.assertIn("PRIVILEGE_ESCALATION_NOT_DISABLED",self.check(c)["issues"])
 def test_missing_privilege_protection_holds(self):
  c=config();c["HostConfig"]["SecurityOpt"]=[]
  self.assertIn("PRIVILEGE_ESCALATION_NOT_DISABLED",self.check(c)["issues"])
 def test_cap_drop_holds(self):
  c=config();c["HostConfig"]["CapDrop"]=[]
  self.assertIn("CAPABILITIES_NOT_DROPPED",self.check(c)["issues"])
 def test_invalid_payload_holds(self):
  self.assertFalse(self.check(c={})["local_preflight_pass"])
 def test_no_paths_or_private_data_in_result(self):
  c=config();c["Config"]["private"]="SECRET";c["Mounts"].append({"Destination":"/private/secrets"})
  x=json.dumps(self.check(c))
  self.assertNotIn("SECRET",x);self.assertNotIn("/private/",x)
 def test_unreadable_docker_holds(self):
  with patch.object(r,"_docker_inspect",side_effect=OSError("private")):
   x=r.inspect_local("fake","/private")
  self.assertIn("READONLY_INSPECTION_UNAVAILABLE",x["issues"])
 def test_readonly_healthy_network_inspection(self):
  with patch.object(r,"_docker_inspect",return_value=config()):
   class Stub:
    returncode=0
    stdout='[{"Internal":true}]'
   with patch.object(r.subprocess,"run",return_value=Stub()) as call:
    with patch.object(r.cowrie_log_health,"assess",return_value=healthy()):
     with patch.object(r,"_mounted_var_matches",return_value=True):
      x=r.inspect_local("fake","/private")
  self.assertTrue(x["local_preflight_pass"])
  self.assertEqual(call.call_args[0][0][:3],["docker","network","inspect"])
 def test_missing_real_var_mount_holds(self):
  c=config();c["Mounts"]=[]
  self.assertFalse(r._mounted_var_matches(c,"/tmp/fake"))
 def test_volume_must_be_writable(self):
  c=config();c["Mounts"]=[{"Destination":"/cowrie/cowrie-git/var","Type":"bind","RW":False,"Source":"/tmp/fake"}]
  self.assertFalse(r._mounted_var_matches(c,"/tmp/fake"))
 def test_mismatched_var_source_refused(self):
  c=config()
  c["Mounts"]=[{"Destination":"/cowrie/cowrie-git/var","Type":"bind","RW":True,"Source":"/tmp/untrusted-other"}]
  with patch.object(r,"_docker_inspect",return_value=c):
   with patch.object(r.subprocess,"run",return_value=type("S",(),{"returncode":0,"stdout":'[{"Internal":true}]'})()):
    with patch.object(r.cowrie_log_health,"assess",return_value=healthy()):
     with patch.object(r,"_mounted_var_matches",return_value=False):
      verdict=r.inspect_local("fake","/tmp/safe")
  self.assertIn("LOG_VOLUME_SOURCE_NOT_CONFIRMED",verdict["issues"])
  self.assertFalse(verdict["local_preflight_pass"])
 def test_samefile_actual_var_mount(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   c=config()
   c["Mounts"]=[{"Destination":"/cowrie/cowrie-git/var","Type":"bind","RW":True,"Source":d}]
   self.assertTrue(r._mounted_var_matches(c,d))
if __name__=="__main__":unittest.main()
