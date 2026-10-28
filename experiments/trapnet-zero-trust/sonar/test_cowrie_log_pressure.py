import json
from unittest.mock import patch,Mock
import unittest
import cowrie_log_pressure as pressure

class CowriePressureLogHealthTests(unittest.TestCase):
    def test_healthy_checker_parsed_without_raw_logs(self):
        reply=Mock(returncode=0,stdout=json.dumps({
            "schema":"trapnet.cowrie-log-health.v1","passed":True,
            "issues":[],"log_entries":3}))
        with patch.object(pressure.subprocess,"run",return_value=reply) as run:
            healthy,report=pressure.probe_private_log_health("isolated-cowrie")
        self.assertTrue(healthy)
        self.assertEqual(report["log_entries"],3)
        args=run.call_args.args[0]
        self.assertEqual(args[:3],["docker","exec","-i"])
        self.assertNotIn("--privileged",args)
    def test_low_space_is_an_expected_report_not_a_crash(self):
        reply=Mock(returncode=3,stdout=json.dumps({
            "schema":"trapnet.cowrie-log-health.v1","passed":False,
            "issues":["FREE_SPACE_LOW"]}))
        with patch.object(pressure.subprocess,"run",return_value=reply):
            healthy,report=pressure.probe_private_log_health("isolated-cowrie")
        self.assertFalse(healthy)
        self.assertIn("FREE_SPACE_LOW",report["issues"])
    def test_unexpected_result_refused(self):
        reply=Mock(returncode=0,stdout='{"schema":"unexpected"}')
        with patch.object(pressure.subprocess,"run",return_value=reply):
            with self.assertRaises(ValueError):
                pressure.probe_private_log_health("isolated-cowrie")
    def test_tool_error_refused(self):
        reply=Mock(returncode=2,stdout='')
        with patch.object(pressure.subprocess,"run",return_value=reply):
            with self.assertRaises(RuntimeError):
                pressure.probe_private_log_health("isolated-cowrie")

if __name__=="__main__":unittest.main()
