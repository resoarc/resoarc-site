#!/usr/bin/env python3
"""Anonymous negative/positive E1 retention evidence for disposable Linux CI."""
import io
import json
from pathlib import Path
import sys
import unittest

HOME=Path(__file__).resolve().parent
sys.path.insert(0,str(HOME))

def main():
    cases=unittest.defaultTestLoader.discover(str(HOME),pattern="test_retention_offline.py")
    output=io.StringIO()
    report=unittest.TextTestRunner(stream=output,verbosity=1).run(cases)
    success=report.wasSuccessful() and report.testsRun==14 and not report.skipped
    outcome={"schema":"trapnet.offline-log-retention-acceptance.v060",
       "passed":success,"checks_passed":report.testsRun-len(report.failures)-len(report.errors)-len(report.skipped),
       "checks_expected":14,
       "dry_run_default_tested":success,
       "explicit_hash_approval_tested":success,
       "symlink_and_hardlink_rejected":success,
       "recent_files_preserved":success,
       "synthetic_only":True,"production_modified":False,
       "formal_E1_release_pass":False,"release_approved":False}
    print(json.dumps(outcome,sort_keys=True))
    return 0 if success else 3
if __name__=="__main__":
    sys.exit(main())
