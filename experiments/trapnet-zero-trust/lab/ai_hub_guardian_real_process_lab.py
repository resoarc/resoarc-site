#!/usr/bin/env python3
"""v0.56: real compiled HUB + Guardian, synthetic AI advisory non-authority.

Offline synthetic data only. Uses disposable directories, ephemeral in-memory
signer keys, and an unoccupied 127.0.0.1 port. No live TrapNet service is touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sonar"))
from ai_response_quarantine import process_json
from safe_analysis_input import to_advisory_packet

SCHEMA = "trapnet.real-process-ai-isolation.v056"

def assert_true(name, condition, checks):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def run(args, timeout=40):
    return subprocess.run([str(x) for x in args], cwd=ROOT, capture_output=True,
                          text=True, stdin=subprocess.DEVNULL, timeout=timeout, check=False)

def file_sha(path):
    path = pathlib.Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def packet_and_quarantine():
    # Use exactly the trusted aggregate -> advisory -> model-output gate from v0.54.
    report = {
      "schema": "trapnet.public-aggregate.v1",
      "privacy": {"raw_ip_exported": False, "node_ids_exported": False,
                  "raw_ua_exported": False, "raw_path_exported": False,
                  "raw_headers_exported": False, "small_counts_suppressed": True},
      "observations_band": "10-49",
      "path_category_bands": {"api": "5-9"},
      "status_family_bands": {"4xx": "10-49"},
      "small_cohorts_omitted": True,
      "classification": "unverified_observation_not_attack",
    }
    model = {"schema": "trapnet.ai-hypothesis.v1",
             "advisory_code": "review_api_activity", "confidence": "low"}
    quarantined = process_json(json.dumps(to_advisory_packet(report)), json.dumps(model))
    if quarantined["allowed_actions"] != [] or quarantined["can_sign_feeds"]:
        raise AssertionError("AI output unexpectedly gained authority")
    return json.dumps(model).encode(), json.dumps(quarantined).encode()

def post_local(url, data):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code

def call_guardian(binary, root, feed_path):
    # Lab-only experimental legacy -pub mode; no release-mode policy claim.
    return run([binary, "-feed", feed_path, "-pub", root / "fixtures" / "feed_pub.hex",
                "-state", root / "guardian.state"], timeout=10)

def check_hub(bin_dir, base, model_raw, quarantined_raw, checks):
    # The real HUB intentionally refuses any port except fixed loopback 8788.
    port = 8788
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError("refuse to reuse an occupied HUB test port")
    host = "127.0.0.1"
    url = "http://" + host + ":" + str(port)
    fixtures = base / "fixtures"
    ledger = base / "ledger.jsonl"
    command = [bin_dir / "hub", "-listen", host + ":" + str(port),
               "-allowlist", fixtures / "allowlist.json", "-ledger", ledger]
    proc = subprocess.Popen([str(a) for a in command], cwd=ROOT, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ready = False
        for _ in range(80):
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(url + "/health", timeout=0.3) as r:
                    if r.status == 200:
                        ready = True
                        break
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.08)
        assert_true("real_loopback_hub_healthy", ready and proc.poll() is None, checks)
        assert_true("empty_hub_ledger", ledger.exists() and ledger.stat().st_size == 0, checks)
        old_hash = file_sha(ledger)
        initial_head_hash = file_sha(base / "ledger.jsonl.head")
        inputs = (
            ("raw_model_reply", model_raw),
            ("quarantined_model_reply", quarantined_raw),
            ("unauthorized_control_field", json.dumps({
                 "report": {"kind": "disable_guardian"}, "signature": "spoof",
                 "can_trigger_blocking": True}).encode()),
            ("malformed_json", b'{"report":\x00}'),
            ("huge_payload", b'{"untrusted":"' + b"X" * 9000 + b'"}'),
        )
        for name, raw in inputs:
            status = post_local(url + "/report", raw)
            assert_true("hub_rejects_" + name, status in (400, 403, 413), checks)
            assert_true("hub_ledger_unchanged_before_" + name, file_sha(ledger) == old_hash, checks)
            assert_true("hub_checkpoint_unchanged_before_" + name,
                        file_sha(base / "ledger.jsonl.head") == initial_head_hash, checks)
        assert_true("hub_initial_checkpoint_stable",
                    file_sha(base / "ledger.jsonl.head") == initial_head_hash, checks)

        good = (fixtures / "report_valid.json").read_bytes()
        assert_true("real_signed_sensor_control_accepted",
                    post_local(url + "/report", good) == 202, checks)
        assert_true("real_ledger_one_authorized_record",
                    len(ledger.read_text(encoding="utf-8").splitlines()) == 1, checks)
        locked_hash = file_sha(ledger)
        head_hash = file_sha(base / "ledger.jsonl.head")
        assert_true("hub_checkpoint_created", head_hash is not None, checks)
        bad_files = ("report_unsigned.json", "report_tampered.json", "report_unregistered.json")
        for fname in bad_files:
            status = post_local(url + "/report", (fixtures / fname).read_bytes())
            assert_true("hub_rejects_" + fname, status in (400, 403), checks)
            assert_true("hub_ledger_preserved_after_" + fname,
                        file_sha(ledger) == locked_hash and
                        file_sha(base / "ledger.jsonl.head") == head_hash, checks)
        assert_true("hub_replay_rejected", post_local(url + "/report", good) == 409, checks)
        assert_true("hub_replay_preserves_ledger",
                    file_sha(ledger) == locked_hash and
                    file_sha(base / "ledger.jsonl.head") == head_hash, checks)
        with urllib.request.urlopen(url + "/health", timeout=2) as resp:
            assert_true("hub_survives_rejected_input", resp.status == 200, checks)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)

def check_guardian(bin_dir, root, model_raw, quarantined_raw, checks):
    fixtures = root / "fixtures"
    for name, raw in (("raw_model", model_raw), ("quarantined_model", quarantined_raw),
                      ("role_spoof", b'{"role":"system","signature":"spoof"}'),
                      ("malformed", b'{"feed":')):
        candidate = root / ("ai_" + name + ".json")
        candidate.write_bytes(raw)
        result = call_guardian(bin_dir / "guardian", root, candidate)
        assert_true("guardian_rejects_" + name, result.returncode != 0, checks)
        assert_true("guardian_state_absent_after_" + name,
                    not (root / "guardian.state").exists(), checks)
    good = fixtures / "feed_valid.json"
    verified = call_guardian(bin_dir / "guardian", root, good)
    assert_true("real_signed_feed_control_accepted", verified.returncode == 0, checks)
    state = root / "guardian.state"
    assert_true("guardian_state_version_1",
                json.loads(state.read_text(encoding="utf-8"))["version"] == 1, checks)
    immutable = file_sha(state)
    for fname in ("feed_unsigned.json", "feed_tampered.json",
                  "feed_untrusted_signer.json", "feed_rollback.json"):
        result = call_guardian(bin_dir / "guardian", root, fixtures / fname)
        assert_true("guardian_rejects_" + fname, result.returncode != 0, checks)
        assert_true("guardian_state_unchanged_after_" + fname,
                    file_sha(state) == immutable, checks)
    same = call_guardian(bin_dir / "guardian", root, good)
    assert_true("guardian_same_signed_version_idempotent", same.returncode == 0, checks)
    assert_true("guardian_idempotence_does_not_mutate_state",
                file_sha(state) == immutable, checks)

def verify_runtime_isolation(bin_dir, checks):
    # Observable restrictions, not merely Docker CLI options.
    import errno
    assert_true("sandbox_nonroot", os.getuid() == 65534 and os.getgid() == 65534, checks)
    assert_true("sandbox_readonly_source", bool(os.statvfs(str(ROOT)).f_flag & os.ST_RDONLY), checks)
    assert_true("sandbox_readonly_prebuilt_bins",
                bool(os.statvfs(str(bin_dir)).f_flag & os.ST_RDONLY), checks)
    assert_true("sandbox_readonly_root", bool(os.statvfs("/").f_flag & os.ST_RDONLY), checks)
    assert_true("docker_socket_not_mounted",
                not pathlib.Path("/var/run/docker.sock").exists(), checks)
    st = {}
    for line in pathlib.Path("/proc/self/status").read_text(encoding="ascii").splitlines():
        if ":" in line:
            k,v = line.split(":",1)
            st[k] = v.strip()
    assert_true("sandbox_zero_caps", int(st.get("CapEff","-1"),16) == 0, checks)
    assert_true("sandbox_no_new_privileges", st.get("NoNewPrivs")=="1", checks)
    assert_true("sandbox_seccomp_active", st.get("Seccomp")=="2", checks)
    assert_true("sandbox_only_loopback_interface",
                set(os.listdir("/sys/class/net")) == {"lo"}, checks)
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(("192.0.2.1",443))
    assert_true("sandbox_no_nonloopback_connect",
                result not in (0, errno.ETIMEDOUT), checks)
    assert_true("sandbox_no_provider_tokens", not any(os.environ.get(k) for k in (
        "GITHUB_TOKEN", "GH_TOKEN", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
        "OPENAI_API_KEY", "GOOGLE_API_KEY", "AWS_SECRET_ACCESS_KEY")), checks)
    for name in ("/", str(ROOT), str(bin_dir)):
        assert_true("sandbox_no_writes_" + name.replace("/","_"),
                    bool(os.statvfs(name).f_flag & os.ST_RDONLY), checks)


def lab():
    checks = []
    model, quarantined = packet_and_quarantine()
    with tempfile.TemporaryDirectory(prefix="trapnet-real-ai-boundary-") as tmp:
        root = pathlib.Path(tmp)
        root.chmod(0o700)
        provided = os.environ.get("TRAPNET_E2_BIN_DIR")
        if provided:
            bin_dir = pathlib.Path(provided)
            assert_true("external_ci_bins_readonly",
                        all((bin_dir / n).is_file() and os.access(bin_dir / n, os.X_OK)
                            for n in ("hub", "guardian", "fixture")), checks)
            verify_runtime_isolation(bin_dir, checks)
        else:
            bin_dir = root / "bin"
            bin_dir.mkdir(mode=0o700)
            for name, path in (("hub", "./cmd/hub"), ("guardian", "./cmd/guardian"),
                               ("fixture", "./lab/ai_hub_guardian_fixture")):
                result = run(["go", "build", "-trimpath", "-o", bin_dir / name, path], timeout=120)
                assert_true("compiled_" + name, result.returncode == 0, checks)
        fixtures = root / "fixtures"
        fixtures.mkdir(mode=0o700)
        result = run([bin_dir / "fixture", "-out", fixtures])
        assert_true("ephemeral_synthetic_signers_created_in_memory", result.returncode == 0, checks)
        assert_true("private_keys_not_written",
                    not any("private" in f.name or f.suffix == ".key"
                            for f in root.rglob("*") if f.is_file()), checks)
        check_hub(bin_dir, root, model, quarantined, checks)
        check_guardian(bin_dir, root, model, quarantined, checks)
    return {"schema": SCHEMA, "status": "pass", "checks_passed": len(checks),
            "only_loopback_hub_network": True, "actual_go_hub_exercised": True,
            "actual_go_guardian_exercised": True, "valid_signed_controls_accepted": True,
            "model_advisory_operational_authority": False,
            "private_key_material_written": False, "synthetic_only": True,
            "live_ai_service_tested": False, "release_approved": False,
            "production_modified": False}

if __name__ == "__main__":
    try:
        report = lab()
        print(json.dumps(report, sort_keys=True))
    except (AssertionError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        safe = str(e) if isinstance(e, AssertionError) and str(e).replace("_", "").isalnum() and len(str(e)) <= 90 else "UNKNOWN"
        print(json.dumps({"schema": SCHEMA, "status": "fail",
                          "error_class": type(e).__name__, "failure_step": safe,
                          "release_approved": False}, sort_keys=True))
        sys.exit(3)
