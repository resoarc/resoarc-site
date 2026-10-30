#!/usr/bin/env python3
"""Quarantine-only, offline boundary for OPTIONAL model-generated advisory codes.

Not an AI caller. No code path sends to HUB, signs feeds, invokes Guardian, or
executes model text. This module emits small enumerated status only to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import stat
import sys

try:
    from .safe_analysis_input import parse_strict_json, BANDS, CATEGORIES, STATUSES
except ImportError:
    from safe_analysis_input import parse_strict_json, BANDS, CATEGORIES, STATUSES

PACKET_SCHEMA = "trapnet.ai-advisory-aggregate.v1"
RESPONSE_SCHEMA = "trapnet.ai-hypothesis.v1"
OUTPUT_SCHEMA = "trapnet.ai-offline-review.v1"
PACKET_MAX_BYTES = 4096
RESPONSE_MAX_BYTES = 1024

PACKET_FIELDS = frozenset((
    "schema", "trust", "observation_band", "categories", "statuses",
    "allowed_actions", "can_trigger_blocking", "can_execute_commands",
    "requires_human_review", "ai_pipeline_integration_verified",
))
RESPONSE_FIELDS = frozenset(("schema", "advisory_code", "confidence"))
CODES = frozenset((
    "insufficient_evidence",
    "review_auth_activity",
    "review_config_activity",
    "review_api_activity",
    "review_http_errors",
    "review_data_integrity",
))
CONFIDENCES = frozenset(("unknown", "low", "medium"))
CONTEXT = {
    "review_auth_activity": ("categories", "auth"),
    "review_config_activity": ("categories", "config"),
    "review_api_activity": ("categories", "api"),
    "review_http_errors": ("statuses", "4xx", "5xx"),
}
NO_AUTHORITY = {
    "allowed_actions": [],
    "can_trigger_blocking": False,
    "can_execute_commands": False,
    "requires_human_review": True,
    "sent_to_hub": False,
    "sent_to_guardian": False,
    "can_sign_feeds": False,
    "ai_pipeline_integration_verified": False,
    "release_approved": False,
}

def _fail():
    # Never echo a model-generated string, path, IP, user agent, or token.
    raise ValueError("untrusted input rejected")

def _strict_mapping(value, fields):
    if type(value) is not dict or set(value) != fields:
        _fail()

def validate_packet(packet):
    _strict_mapping(packet, PACKET_FIELDS)
    if (packet["schema"] != PACKET_SCHEMA or
        packet["trust"] != "untrusted_aggregate_not_verified_attack" or
        type(packet["observation_band"]) is not str or
        packet["observation_band"] not in BANDS or
        packet["allowed_actions"] != [] or
        type(packet["allowed_actions"]) is not list or
        packet["can_trigger_blocking"] is not False or
        packet["can_execute_commands"] is not False or
        packet["requires_human_review"] is not True or
        packet["ai_pipeline_integration_verified"] is not False):
        _fail()
    for field, whitelist in (("categories", CATEGORIES), ("statuses", STATUSES)):
        value = packet[field]
        if type(value) is not dict or not set(value).issubset(whitelist):
            _fail()
        if any(type(v) is not str or v not in BANDS for v in value.values()):
            _fail()
    return packet

def validate_hypothesis(packet, response):
    """Validate a model hypothesis, but return NO commands or free text."""
    validate_packet(packet)
    _strict_mapping(response, RESPONSE_FIELDS)
    if (response["schema"] != RESPONSE_SCHEMA or
        type(response["advisory_code"]) is not str or
        response["advisory_code"] not in CODES or
        type(response["confidence"]) is not str or
        response["confidence"] not in CONFIDENCES):
        _fail()
    code = response["advisory_code"]
    if packet["observation_band"] == "<5" and code != "insufficient_evidence":
        _fail()
    if code in CONTEXT:
        field, *required = CONTEXT[code]
        if not any(key in packet[field] for key in required):
            _fail()
    if code == "review_data_integrity":
        # Source integrity is separate signed evidence; aggregate alone cannot establish it.
        _fail()
    if code == "insufficient_evidence" and response["confidence"] != "unknown":
        _fail()
    canonical = json.dumps(packet, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    result = {
        "schema": OUTPUT_SCHEMA,
        "status": "quarantined_advisory",
        "advisory_code": code,
        "confidence": response["confidence"],
        "packet_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    result.update(NO_AUTHORITY)
    return result

def _read_bounded_regular_file(path, limit):
    p = pathlib.Path(path)
    if p.is_symlink():
        _fail()
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(p, flags)
        try:
            information = os.fstat(fd)
            if not stat.S_ISREG(information.st_mode) or information.st_size > limit:
                _fail()
            with os.fdopen(fd, "rb") as stream:
                fd = -1
                data = stream.read(limit + 1)
            if len(data) > limit:
                _fail()
            return data.decode("utf-8", errors="strict")
        finally:
            if fd >= 0:
                os.close(fd)
    except (OSError, UnicodeError, OverflowError):
        _fail()

def process_json(packet_text, response_text):
    if type(packet_text) is not str or type(response_text) is not str:
        _fail()
    if len(packet_text.encode("utf-8")) > PACKET_MAX_BYTES or len(response_text.encode("utf-8")) > RESPONSE_MAX_BYTES:
        _fail()
    try:
        packet = parse_strict_json(packet_text)
        response = parse_strict_json(response_text)
    except (ValueError, TypeError, RecursionError):
        _fail()
    return validate_hypothesis(packet, response)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Offline, no-network, quarantine-only AI advisory boundary")
    ap.add_argument("--packet", required=True, help="Only a privacy-safe, validated advisory aggregate")
    ap.add_argument("--model-response", required=True, help="Untrusted model-produced JSON, never raw logs")
    args = ap.parse_args(argv)
    try:
        packet = _read_bounded_regular_file(args.packet, PACKET_MAX_BYTES)
        response = _read_bounded_regular_file(args.model_response, RESPONSE_MAX_BYTES)
        result = process_json(packet, response)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (ValueError, TypeError, UnicodeError):
        rejection = dict({"schema": OUTPUT_SCHEMA, "status": "rejected"}, **NO_AUTHORITY)
        print(json.dumps(rejection, sort_keys=True, separators=(",", ":")))
        return 2

if __name__ == "__main__":
    sys.exit(main())
