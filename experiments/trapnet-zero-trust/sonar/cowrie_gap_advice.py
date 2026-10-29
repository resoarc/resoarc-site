#!/usr/bin/env python3
"""Read-only operator aid mapping bounded Cowrie health failures to gap types.

Does not send any network data, inspect raw private events in output,
clear a previous gap or assert healthy coverage. Only returns categorical
advice; the signed Sensor notice remains an explicit operator action.
"""
import argparse
import json
import cowrie_log_health

SCHEMA="trapnet.cowrie-gap-operator-advice.v1"

# Ordered worst-case precedence for deterministic, conservative advice.
FAILURE_CATEGORIES=(
    ("storage_full",frozenset({"FREE_SPACE_LOW"})),
    ("log_corrupt",frozenset({"JSON_LINE_INVALID","JSON_EVENT_INVALID",
                            "JSON_LOG_EMPTY","JSON_LOG_TOO_LARGE","JSON_LOG_NO_EVENTS",
                            "JSON_LINE_DUPLICATE"})),
    ("log_unavailable",frozenset({"JSON_LOG_MISSING","IO_OR_FORMAT_ERROR",
                                  "LOG_PATH_SYMLINK","VAR_ROOT_UNSAFE","JSON_LOG_TYPE_UNSAFE"})),
)
def decide(health):
    codes=set()
    if not isinstance(health,dict) or health.get("schema")!="trapnet.cowrie-log-health.v1":
        return {"schema":SCHEMA,"status":"INSPECTION_HOLD",
                "gap_notice_recommended":False,"gap_reason":None,
                "observation_coverage_proven":False,"automatic_send":False,
                "automatic_clear":False}
    raw=health.get("issues")
    if not isinstance(raw,list) or any(not isinstance(v,str) for v in raw):
        return {"schema":SCHEMA,"status":"INSPECTION_HOLD",
                "gap_notice_recommended":False,"gap_reason":None,
                "observation_coverage_proven":False,"automatic_send":False,
                "automatic_clear":False}
    codes=set(raw)
    reason=None
    for category,reasons in FAILURE_CATEGORIES:
        if codes&reasons:
            reason=category
            break
    # "passed" only proves a bounded, parseable snapshot at one time,
    # not true completeness, liveness or malicious-observation absence.
    if reason is not None:
        status="GAP_NOTICE_RECOMMENDED"
    elif health.get("passed") is True and not codes:
        status="SNAPSHOT_PARSEABLE_COVERAGE_UNPROVEN"
    else:
        status="INSPECTION_HOLD"
    return {"schema":SCHEMA,"status":status,
            "gap_notice_recommended":reason is not None,"gap_reason":reason,
            "observation_coverage_proven":False,"automatic_send":False,
            "automatic_clear":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--private-var",required=True)
    options=parser.parse_args()
    result=decide(cowrie_log_health.assess(options.private_var))
    print(json.dumps(result,sort_keys=True))
    # No case here authorizes the production release; exit is always nonzero.
    return 3

if __name__=="__main__":
    raise SystemExit(main())
