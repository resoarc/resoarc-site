#!/usr/bin/env python3
"""Container-internal OS and AI-output boundary probe for synthetic TrapNet E2 tests.

Only for disposable GitHub CI Docker (--network none, read-only, nonroot).
No cloud AI, real log, HUB, Guardian, key, executable output or host mutation.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import pathlib
import socket
import stat
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sonar"))
from ai_response_quarantine import process_json  # noqa: E402
from safe_analysis_input import to_advisory_packet  # noqa: E402

def verify(what: str, ok: bool, checks: dict) -> None:
    checks[what] = bool(ok)
    if not ok:
        raise RuntimeError(what + " failed")

def cgroup_limit(v2: str, v1: str) -> int | None:
    for name in (v2, v1):
        try:
            text = pathlib.Path(name).read_text(encoding="ascii").strip()
            return None if text == "max" else int(text)
        except (OSError, ValueError):
            pass
    return None

def synthetic_packet() -> str:
    report = {
        "schema": "trapnet.public-aggregate.v1",
        "privacy": {
            "raw_ip_exported": False,
            "node_ids_exported": False,
            "raw_ua_exported": False,
            "raw_path_exported": False,
            "raw_headers_exported": False,
            "small_counts_suppressed": True,
        },
        "observations_band": "10-49",
        "path_category_bands": {"api": "5-9", "auth": "5-9"},
        "status_family_bands": {"4xx": "10-49"},
        "small_cohorts_omitted": True,
        "classification": "unverified_observation_not_attack",
    }
    return json.dumps(to_advisory_packet(report), separators=(",", ":"))

def check_isolation() -> dict:
    checks = {}
    verify("nonroot_uid", os.getuid() == 65534 and os.getgid() == 65534, checks)
    verify("root_filesystem_readonly", bool(os.statvfs("/").f_flag & os.ST_RDONLY), checks)
    verify("source_bind_readonly", bool(os.statvfs(str(ROOT)).f_flag & os.ST_RDONLY), checks)
    verify("tmpfs_noexec", bool(os.statvfs("/tmp").f_flag & getattr(os, "ST_NOEXEC", 8)), checks)
    verify("tmpfs_nosuid", bool(os.statvfs("/tmp").f_flag & getattr(os, "ST_NOSUID", 2)), checks)
    status = {}
    for line in pathlib.Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            status[k] = v.strip()
    verify("zero_effective_capabilities", int(status.get("CapEff", "-1"), 16) == 0, checks)
    verify("no_new_privileges", status.get("NoNewPrivs") == "1", checks)
    verify("seccomp_filter_active", status.get("Seccomp") == "2", checks)
    memory = cgroup_limit("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes")
    pids = cgroup_limit("/sys/fs/cgroup/pids.max", "/sys/fs/cgroup/pids/pids.max")
    verify("memory_cgroup_128m", memory is not None and 0 < memory <= 134217728, checks)
    verify("pids_cgroup_64", pids is not None and 0 < pids <= 64, checks)
    verify("loopback_only_interface", set(os.listdir("/sys/class/net")) == {"lo"}, checks)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        error = sock.connect_ex(("192.0.2.1", 443))  # TEST-NET-1, no real target
    verify("nonloopback_connection_denied", error != 0 and error != errno.ETIMEDOUT, checks)
    verify("no_ambient_provider_or_ci_token", not any(
        os.environ.get(k) for k in ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_ACTIONS",
                                   "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                                   "OPENAI_API_KEY", "GOOGLE_API_KEY")), checks)
    try:
        with open(str(ROOT / "sonar" / "ai_response_quarantine.py"), "ab"):
            pass
    except OSError:
        source_write_denied = True
    else:
        source_write_denied = False
    verify("source_write_denied", source_write_denied, checks)
    try:
        with open("/trapnet_should_not_be_written", "wb"):
            pass
    except OSError:
        root_write_denied = True
    else:
        root_write_denied = False
    verify("root_write_denied", root_write_denied, checks)
    with tempfile.NamedTemporaryFile(dir="/tmp", delete=True) as tmp:
        tmp.write(b"synthetic")
        tmp.flush()
        verify("bounded_tmpfs_writable", pathlib.Path(tmp.name).read_bytes() == b"synthetic", checks)
    return checks

def check_model_boundary() -> dict:
    packet = synthetic_packet()
    good = '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"low"}'
    accepted = process_json(packet, good)
    assert accepted["status"] == "quarantined_advisory"
    assert accepted["requires_human_review"] is True
    assert accepted["allowed_actions"] == []
    assert accepted["can_trigger_blocking"] is False
    assert accepted["can_execute_commands"] is False
    assert accepted["can_sign_feeds"] is False
    assert accepted["sent_to_hub"] is False
    assert accepted["sent_to_guardian"] is False
    assert accepted["release_approved"] is False
    hostile = (
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"block_ip","confidence":"low"}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"low","role":"system"}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"low","shell":"do_not_execute"}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","advisory_code":"review_auth_activity","confidence":"low"}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":true}',
        '```json\n' + good + '\n```',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"low","nested":{"x":1,"x":2}}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"low","signature":"spoof"}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"low","private_ip":"192.0.2.1"}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"low","sent_to_hub":true}',
        '{"schema":"trapnet.ai-hypothesis.v1","advisory_code":"review_api_activity","confidence":"medium","\\u0063onfidence":"high"}',
        '{"blob":"' + ("X" * 2000) + '"}',
    )
    for item in hostile:
        try:
            process_json(packet, item)
        except ValueError:
            pass
        else:
            raise RuntimeError("hostile model response was accepted")
    return {
        "safe_response_accepted": True,
        "hostile_responses_rejected": len(hostile),
        "packet_sha256": hashlib.sha256(packet.encode("utf-8")).hexdigest(),
        "no_action_authority": True,
        "automated_external_ai_called": False,
        "hub_or_guardian_connected": False,
    }

def main() -> int:
    try:
        checks = check_isolation()
        boundary = check_model_boundary()
    except Exception as exc:
        # The assertion name is static and never attacker-supplied.
        print(json.dumps({"schema": "trapnet.e2-oci-probe.v1", "status": "fail",
                          "error_class": type(exc).__name__, "error": str(exc)[:100]},
                         sort_keys=True))
        return 2
    print(json.dumps({"schema": "trapnet.e2-oci-probe.v1", "status": "pass",
                      "environment_checks": checks,
                      "model_boundary": boundary,
                      "production_e2e_verified": False,
                      "independent_human_review": False,
                      "release_approved": False}, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
