import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import cowrie_offline_integration as cowrie

class OfflineCowrieTests(unittest.TestCase):
    def test_requires_immutable_image(self):
        for image in ("cowrie/cowrie:latest","sha256:abc","../../etc/passwd"):
            with self.assertRaises(ValueError):cowrie.image_verified(image)
    def test_rejects_unexpected_declared_volume(self):
        image="sha256:"+"a"*64
        reply=Mock(returncode=0,stdout=json.dumps([{"Id":image,"Config":{"Volumes":{"/var/run/docker.sock":{}}}}]))
        with patch.object(cowrie,"docker",return_value=reply):
            with self.assertRaises(ValueError):cowrie.image_verified(image)
    def test_no_event_without_log(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cowrie.json_events(Path(d)),(0,False))
    def test_synthetic_json_connections(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"log/cowrie"
            p.mkdir(parents=True)
            (p/"cowrie.json").write_text(
                json.dumps({"eventid":"cowrie.session.connect"})+"\n"+
                json.dumps({"eventid":"cowrie.session.closed"})+"\n")
            self.assertEqual(cowrie.json_events(Path(d)),(2,True))
    def test_invalid_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"log/cowrie";p.mkdir(parents=True)
            (p/"cowrie.json").write_text("NOT JSON\n")
            with self.assertRaises(ValueError):cowrie.json_events(Path(d))
    def test_no_public_ports_or_host_network(self):
        image="sha256:"+"a"*64
        fake={"Image":image,"State":{"Running":True},
              "HostConfig":{"NetworkMode":"none","ReadonlyRootfs":True,
                "CapDrop":["ALL"],"SecurityOpt":["no-new-privileges"],
                "PidsLimit":64,"Memory":201326592,"Privileged":False,"PortBindings":None,"CapAdd":None},
              "Mounts":[{"Destination":cowrie.BASE+"/etc","RW":False,"Source":"/private/etc"},
                        {"Destination":cowrie.BASE+"/var","RW":True,"Source":"/private/var"}]}
        reply=Mock(stdout=json.dumps([fake]))
        with patch.object(cowrie,"docker",return_value=reply):
            self.assertTrue(cowrie.confirm_isolation("test",image,Path("/private/etc"),Path("/private/var")))
            fake["HostConfig"]["NetworkMode"]="host"
            reply.stdout=json.dumps([fake])
            with self.assertRaises(ValueError):cowrie.confirm_isolation("test",image,Path("/private/etc"),Path("/private/var"))

if __name__=="__main__":unittest.main()
