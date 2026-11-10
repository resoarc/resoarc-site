#!/usr/bin/env python3
"""Block common accidental secret disclosures in the protected-branch CI.

Scan tracked source and text members of SHA-256-verified distributed ZIPs.
Never print secret values. This is defense in depth, not a substitute for
GitHub secret scanning/push protection and key rotation after an incident.
"""
from __future__ import annotations
import io
import re
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE_FILENAMES = re.compile(
    r"(?:^|/)(?:\.env(?:\..*)?|id_rsa|id_ed25519|credentials\.json|"
    r"secrets?\.(?:json|ya?ml)|[^/]*\.(?:pem|p12|pfx|key))$", re.I)
TEXT_EXT = {".js", ".ts", ".py", ".json", ".md", ".txt", ".html", ".css",
            ".yml", ".yaml", ".xml", ".sh", ".ps1", ".toml", ".properties",
            ".env", ".csv", ".ini", ".cfg"}
PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{30,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe-live-key", re.compile(r"\bsk_live_[0-9A-Za-z]{20,}\b")),
    ("explicit-assignment", re.compile(
        r"""(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password|client_secret)\b\s*[:=]\s*['"][A-Za-z0-9_/+=.-]{26,}['"]""")),
    ("credential-url", re.compile(r"https?://[A-Za-z0-9._~-]{3,}:[^@\s/]{8,}@")),
)
MAX_TEXT_BYTES = 4_000_000

# One previously published, byte-pinned backup source ZIP includes two
# intentionally synthetic Basic Auth URL fixtures in test code. These have
# no corresponding service credentials. Never exempt other ZIPs, test files
# or lines, and reject this exception if any byte of that ZIP changes.
KNOWN_ARCHIVE = "site/downloads/resoarc-backup-migration-v1.0.0-source.zip"
KNOWN_ARCHIVE_SHA256 = "06648e849bb38b9dc5614fbaa507a50492f2684f7015316228df3bfb0e8041fb"
KNOWN_SYNTHETIC_CREDENTIAL_TEST_LINES = {
    (KNOWN_ARCHIVE + "/plugins/backup-migration/tests/qa-guards.test.js", 42):
        "580c1b3ae53ad926a842949d900adcde0dfd0d89dc02e27e595a8fbee0040e96",
    (KNOWN_ARCHIVE + "/plugins/backup-migration/tests/tenant-probe.test.js", 17):
        "cb00a01deb94c40075ac5bae3864f7130c7b349e652f94c6fac26467350ff828",
}


def pinned_synthetic_fixture(label: str, index: int, name: str, line: str) -> bool:
    if name != "credential-url" or (label, index) not in KNOWN_SYNTHETIC_CREDENTIAL_TEST_LINES:
        return False
    expected = KNOWN_SYNTHETIC_CREDENTIAL_TEST_LINES[(label, index)]
    if hashlib.sha256(line.encode("utf-8")).hexdigest() != expected:
        return False
    archive = ROOT / KNOWN_ARCHIVE
    return archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest() == KNOWN_ARCHIVE_SHA256


def findings(label: str, data: bytes) -> list[str]:
    if len(data) > MAX_TEXT_BYTES:
        return [f"{label}: oversized text cannot be scanned"]
    if b"\0" in data[:4096]:
        return []
    lines = data.decode("utf-8", errors="replace").splitlines()
    return [f"{label}:{index}: {name}"
            for index, line in enumerate(lines, 1)
            for name, regex in PATTERNS if regex.search(line)
            and not pinned_synthetic_fixture(label, index, name, line)]


def tracked_files() -> list[str]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                            check=True, capture_output=True)
    return [x.decode("utf-8", errors="replace") for x in result.stdout.split(b"\0") if x]


def check() -> list[str]:
    violations: list[str] = []
    # The twenty historic distribution ZIPs are fetched from a pinned Release
    # before CI: scan their real contents even though they are no longer tracked.
    hydrated_archives = {p.relative_to(ROOT).as_posix()
                         for p in (ROOT / 'site/downloads').glob('*.zip')}
    for relative in sorted(set(tracked_files()) | hydrated_archives):
        path = ROOT / relative
        if SENSITIVE_FILENAMES.search(relative):
            violations.append(f"{relative}: prohibited secret-like tracked filename")
        if not path.is_file():
            violations.append(f"{relative}: missing tracked file")
            continue
        if path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path) as archive:
                    for member in archive.infolist():
                        if member.is_dir() or member.file_size > MAX_TEXT_BYTES:
                            continue
                        name = member.filename
                        if SENSITIVE_FILENAMES.search(name):
                            violations.append(f"{relative}/{name}: prohibited secret-like ZIP filename")
                        if Path(name).suffix.lower() in TEXT_EXT:
                            violations.extend(findings(f"{relative}/{name}", archive.read(member)))
            except zipfile.BadZipFile:
                violations.append(f"{relative}: corrupt distribution ZIP")
        elif path.suffix.lower() in TEXT_EXT or path.name.startswith(".env"):
            violations.extend(findings(relative, path.read_bytes()))
    return violations


if __name__ == "__main__":
    try:
        violations = check()
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"FAIL: secret scanner could not complete: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)
    for item in violations:
        print("FAIL:", item, file=sys.stderr)
    print(f"Secret prevention audit: {len(tracked_files())} tracked paths checked; findings {len(violations)}")
    print("Values are redacted. GitHub secret scanning/push protection and revocation remain separate controls.")
    raise SystemExit(1 if violations else 0)
