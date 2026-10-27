#!/usr/bin/env python3
"""Strict schema boundary for OPTIONAL future AI advisory input.

Do not send attacker-controlled raw access logs, text or credentials to an AI
system. This only produces enumerated aggregate bands. It does NOT grant the
model tools, commands, or an authority to classify an IP as malicious.
"""
import json

CATEGORIES = {"auth","admin","metadata","config","api","database","other"}
STATUSES = {"1xx","2xx","3xx","4xx","5xx","unknown"}
BANDS = {"<5","5-9","10-49","50-99","100-499","500+"}
BASE_FIELDS = {
 "schema","privacy","observations_band","path_category_bands",
 "status_family_bands","small_cohorts_omitted","classification"
}
PASSIVE_FIELDS = {"adapter_schema","source_kind","requires_independent_review",
                  "sent_to_hub","verdict"}
PRIVACY_KEYS = {"raw_ip_exported","node_ids_exported","raw_ua_exported",
                "raw_path_exported","raw_headers_exported","small_counts_suppressed"}

def to_advisory_packet(report):
    if type(report) is not dict or not BASE_FIELDS.issubset(report):
        raise ValueError("unexpected aggregate shape")
    extras = set(report) - BASE_FIELDS
    if extras and extras != PASSIVE_FIELDS:
        raise ValueError("non-aggregate fields forbidden")
    if extras == PASSIVE_FIELDS:
        if (report["adapter_schema"] != "trapnet.passive-import.v0.1" or
            report["source_kind"] not in ("authorized_web_server","authorized_reverse_proxy") or
            report["requires_independent_review"] is not True or
            report["sent_to_hub"] is not False or
            report["verdict"] != "observation_only"):
            raise ValueError("invalid passive provenance flags")
    if report["schema"] != "trapnet.public-aggregate.v1" or \
            report["classification"] != "unverified_observation_not_attack" or \
            report["small_cohorts_omitted"] is not True:
        raise ValueError("untrusted classification")
    privacy = report["privacy"]
    if type(privacy) is not dict or set(privacy) != PRIVACY_KEYS:
        raise ValueError("privacy flags not present")
    for key in PRIVACY_KEYS:
        if privacy[key] is not (key == "small_counts_suppressed"):
            raise ValueError("aggregate privacy contract violated")
    if type(report["observations_band"]) is not str or report["observations_band"] not in BANDS:
        raise ValueError("invalid band")
    paths = report["path_category_bands"]
    statuses = report["status_family_bands"]
    if type(paths) is not dict or type(statuses) is not dict:
        raise ValueError("invalid category structure")
    if (not set(paths).issubset(CATEGORIES) or not set(statuses).issubset(STATUSES) or
        any(type(v) is not str or v not in BANDS for v in list(paths.values())+list(statuses.values()))):
        raise ValueError("unapproved aggregate category or band")
    return {
        "schema":"trapnet.ai-advisory-aggregate.v1",
        "trust":"untrusted_aggregate_not_verified_attack",
        "observation_band":report["observations_band"],
        "categories":{k:paths[k] for k in sorted(paths)},
        "statuses":{k:statuses[k] for k in sorted(statuses)},
        "allowed_actions":[],
        "can_trigger_blocking":False,
        "can_execute_commands":False,
        "requires_human_review":True,
        "ai_pipeline_integration_verified":False
    }

if __name__=="__main__":
    import argparse
    import pathlib
    import sys
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    a=p.parse_args()
    try:
        file=pathlib.Path(a.input)
        if file.is_symlink() or not file.is_file() or file.stat().st_size>16384:
            raise ValueError("unsafe input")
        packet=to_advisory_packet(json.loads(file.read_text(encoding="utf-8")))
        print(json.dumps(packet,sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"accepted":False,"error_class":type(error).__name__}))
        sys.exit(2)