#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import cowrie_gap_lab_bridge as bridge

class DummyResult:
    def __init__(self,rc):self.returncode=rc

class BridgeSafetyTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="gap-bridge-unit-")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.root.chmod(0o700)
        (self.root/bridge.MARKER).write_bytes(b"DISPOSABLE-ONLY\n")
        self.var=self.root/"var";self.var.mkdir(mode=0o700)
        self.spool=self.root/"spool";self.spool.mkdir(mode=0o700)
        self.pending=self.spool/"notice.json"
        self.key=self.root/"private.hex";self.key.write_text("dummy");self.key.chmod(0o600)
        self.sensor=self.root/"sensor";self.sensor.write_text("synthetic test binary")
        self.health={"schema":"trapnet.cowrie-log-health.v1","passed":False,
            "issues":["VOLUME_LIMIT_NOT_PROVEN","JSON_LINE_INVALID"]}
    def send(self,emit=False,rc=1):
        calls=[]
        def runner(args,**kwargs):
            calls.append((args,kwargs))
            return DummyResult(rc)
        with patch.object(bridge.cowrie_log_health,"assess",return_value=self.health):
            result=bridge.execute(self.root,self.var,self.pending,self.key,self.sensor,emit=emit,runner=runner)
        return result,calls
    def test_unsafe_log_suppressed_from_output(self):
        self.health["raw"]="password secret"
        r,c=self.send()
        self.assertNotIn("secret",str(r))
        self.assertFalse(c)
    def test_corrupt_report_suggested_no_send(self):
        r,c=self.send()
        self.assertEqual(r["gap_reason"],"log_corrupt")
        self.assertEqual(r["status"],"HOLD_MANUAL_SEND_NOT_ARMED")
        self.assertFalse(c)
    def test_explicit_send_uses_fixed_argv_no_shell(self):
        r,c=self.send(emit=True)
        self.assertEqual(r["status"],"HOLD_PENDING_DELIVERY")
        self.assertEqual(len(c),1)
        args,kw=c[0]
        self.assertEqual(args[0],str(self.sensor))
        self.assertEqual(args[args.index("-gap-reason")+1],"log_corrupt")
        self.assertEqual(args[args.index("-gap-outbox")+1],str(self.pending))
        self.assertEqual(kw["timeout"],12)
        self.assertNotIn("shell",kw)
    def test_only_202_sender_success_is_reported(self):
        r,c=self.send(emit=True,rc=0)
        self.assertEqual(r["status"],"LAB_202_ACK_RECEIVED")
        self.assertTrue(r["notification_sent"])
    def test_healthy_does_not_auto_clear(self):
        self.health={"schema":"trapnet.cowrie-log-health.v1","passed":True,"issues":[]}
        r,c=self.send(emit=True)
        self.assertEqual(r["status"],"HOLD_NO_VERIFIED_GAP_REASON")
        self.assertFalse(c)
    def test_missing_marker_holds(self):
        (self.root/bridge.MARKER).unlink()
        r,c=self.send(emit=True)
        self.assertEqual(r["status"],"HOLD_LAB_PRECONDITION_OR_IO_FAILURE")
        self.assertFalse(c)
    def test_symlink_marker_refused(self):
        marker=self.root/bridge.MARKER;marker.unlink()
        target=self.root/"mark";target.write_bytes(b"DISPOSABLE-ONLY\n")
        try:marker.symlink_to(target)
        except OSError:self.skipTest("symlink unsupported")
        r,c=self.send(emit=True)
        self.assertFalse(c)
    def test_world_writable_lab_refused(self):
        if os.name!="posix":self.skipTest("POSIX-only permissions")
        self.root.chmod(0o777)
        r,c=self.send(emit=True)
        self.assertFalse(c)
    def test_key_exposed_refused(self):
        if os.name!="posix":self.skipTest("POSIX-only permissions")
        self.key.chmod(0o644)
        r,c=self.send(emit=True)
        self.assertFalse(c)
    def test_existing_pending_refused(self):
        self.pending.write_text("signed outstanding")
        r,c=self.send(emit=True)
        self.assertEqual(r["status"],"HOLD_LAB_PRECONDITION_OR_IO_FAILURE")
        self.assertFalse(c)
    def test_stale_lock_refused(self):
        Path(str(self.pending)+".lock").write_text("unresolved")
        r,c=self.send(emit=True)
        self.assertFalse(c)
    def test_escaped_var_refused(self):
        outside=Path(tempfile.gettempdir())
        with patch.object(bridge.cowrie_log_health,"assess",return_value=self.health):
            r=bridge.execute(self.root,outside,self.pending,self.key,self.sensor,emit=True)
        self.assertEqual(r["status"],"HOLD_LAB_PRECONDITION_OR_IO_FAILURE")
    def test_symlink_outbox_refused(self):
        target=self.spool/"target";target.write_text("do not touch")
        try:self.pending.symlink_to(target)
        except OSError:self.skipTest("symlink unsupported")
        r,c=self.send(emit=True)
        self.assertFalse(c)
        self.assertEqual(target.read_text(),"do not touch")
    def test_runner_error_does_not_claim_success(self):
        with patch.object(bridge.cowrie_log_health,"assess",return_value=self.health):
            with patch.object(bridge.subprocess,"run",side_effect=subprocess.TimeoutExpired("sensor",10)):
                r=bridge.execute(self.root,self.var,self.pending,self.key,self.sensor,emit=True)
        self.assertEqual(r["status"],"HOLD_LAB_PRECONDITION_OR_IO_FAILURE")
        self.assertFalse(r["notification_sent"])

if __name__=="__main__":unittest.main()
