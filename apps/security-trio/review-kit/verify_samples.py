"""Offline, source-only self-check of known synthetic Security Trio fixtures.

Not a third-party assessment, EXE test, GUI test, Authenticode check or release.
Only fixtures identical to the generator's built-in synthetic data are accepted.
This script never sends information, opens untrusted executables or overwrites reports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

import file_inspector  # noqa: E402
import log_lantern  # noqa: E402
import secret_scout  # noqa: E402
from generate_samples import SAMPLES, create_samples  # noqa: E402

MAX_INPUT_SIZE = 1024 * 1024
MAX_MANIFEST_SIZE = 128 * 1024
FIXTURE_NAMES = frozenset((*SAMPLES, "manifest.json"))


class ReviewKitError(ValueError):
    """The selected directory is not an untouched, generated synthetic kit."""


def _read_manifest(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_SIZE:
        raise ReviewKitError("invalid synthetic manifest")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReviewKitError("invalid synthetic manifest type")
    return value


def verify_unchanged_synthetic_samples(directory: Path) -> dict:
    """Require exact generated sample names, manifest, sizes and SHA-256 hashes."""
    if directory.is_symlink() or not directory.is_dir():
        raise ReviewKitError("missing or redirected synthetic review directory")
    children = list(directory.iterdir())
    if {p.name for p in children} != FIXTURE_NAMES or len(children) != len(FIXTURE_NAMES):
        raise ReviewKitError("unexpected sample names")
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_INPUT_SIZE for p in children):
        raise ReviewKitError("sample must be a small regular file")
    manifest = _read_manifest(directory / "manifest.json")
    if manifest.get("type") != "SYNTHETIC_LOCAL_REVIEW_ONLY":
        raise ReviewKitError("refusing non-synthetic samples")
    with tempfile.TemporaryDirectory(prefix="security-trio-known-samples-") as root:
        expected = create_samples(Path(root) / "fixtures")
    if manifest != expected:
        raise ReviewKitError("sample manifest differs from canonical synthetic reference")
    for name in SAMPLES:
        actual_sha = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if actual_sha != expected["files_sha256"][name]:
            raise ReviewKitError("sample bytes differ from canonical synthetic reference")
    return manifest


def run_self_check(directory: Path) -> dict:
    """Only report fixed case IDs, boolean checks and fixed-size counts."""
    verify_unchanged_synthetic_samples(directory)
    results: list[dict] = []

    def record(case_id: str, passed: bool, observed: dict | None = None) -> None:
        results.append({
            "case_id": case_id,
            "status": "PASS" if passed else "FAIL",
            "observed": observed or {},
        })

    secret = secret_scout.scan([directory / "secret-review.env"])
    secret_export = json.dumps(secret.export_data(), ensure_ascii=False)
    record(
        "secret_mock_assignment_redacted",
        any(f.rule == "機密値を含む設定" for f in secret.findings)
        and "DemoOnlyNotReal42" not in secret_export,
        {"findings_count": len(secret.findings)},
    )

    placeholder = secret_scout.scan([directory / "secret-placeholder.env"])
    record("secret_placeholder_ignored", not placeholder.findings)

    archive = secret_scout.scan([directory / "archive-review.zip"])
    archive_rules = {f.rule for f in archive.findings}
    record(
        "secret_zip_detection_without_extraction",
        "機密値を含む設定" in archive_rules
        and "ZIP内の危険なパス" in archive_rules
        and not (directory / "escape.txt").exists(),
        {"findings_count": len(archive.findings)},
    )

    activity = log_lantern.scan([directory / "access-review.log"])
    activity_rules = {f.rule for f in activity.findings}
    activity_export = json.dumps(activity.export_data(), ensure_ascii=False)
    record(
        "log_suspicious_requests_redacted",
        activity.metrics.get("requests") == 15
        and any("秘密" in rule for rule in activity_rules)
        and any("404" in rule for rule in activity_rules)
        and "DemoQueryShouldHide55" not in activity_export
        and "198.51.100.12" not in activity_export,
        {"requests_count": activity.metrics.get("requests"), "findings_count": len(activity.findings)},
    )

    normal = log_lantern.scan([directory / "normal-access.log"])
    record(
        "log_normal_request",
        normal.metrics.get("requests") == 1 and not normal.findings,
        {"requests_count": normal.metrics.get("requests")},
    )

    pdf = file_inspector.scan([directory / "pdf-marker-review.pdf"])
    record("file_pdf_static_marker", any("PDF" in f.rule for f in pdf.findings))

    mismatch = file_inspector.scan([directory / "mismatch-review.pdf"])
    record("file_format_mismatch", any("不一致" in f.rule for f in mismatch.findings))

    double = file_inspector.scan([directory / "double-extension.pdf.exe"])
    record("file_double_extension", any("二重" in f.rule for f in double.findings))

    plain = file_inspector.scan([directory / "plain-review.txt"])
    record("file_harmless_text", not plain.findings)

    return {
        "schema_version": 1,
        "kind": "INTERNAL_SOURCE_ONLY_SYNTHETIC_SELF_CHECK",
        "source_review_only": True,
        "existing_unsigned_binaries_verified": False,
        "external_review_verified": False,
        "signpath_approved": False,
        "candidate_release_authorized": False,
        "overall_status": "PASS" if all(x["status"] == "PASS" for x in results) else "FAIL",
        "case_count": len(results),
        "cases": results,
        "manual_gui_review": "NOT_PERFORMED",
        "manual_human_source_review": "NOT_PERFORMED",
        "note": "Synthetic sample self-check, not a substitute for independent usage, security audit or human release approval.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, required=True,
                        help="Previously generated, unchanged synthetic sample directory")
    parser.add_argument("--report", type=Path,
                        help="Optional NEW report JSON outside the sample directory; never overwritten")
    args = parser.parse_args(argv)
    try:
        output = None
        if args.report:
            output = args.report
            if output.is_symlink() or output.exists() or not output.parent.is_dir():
                raise ReviewKitError("report destination must be a new file in an existing directory")
            samples_resolved = args.samples.resolve(strict=True)
            report_resolved = output.resolve(strict=False)
            if samples_resolved == report_resolved or samples_resolved in report_resolved.parents:
                raise ReviewKitError("report must not be written inside synthetic sample directory")
        result = run_self_check(args.samples)
        encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if output:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
            print("Review-kit synthetic self-check: " + result["overall_status"])
            print("No user files, paths, sample contents or credentials included in report.")
        else:
            print(encoded, end="")
        return 0 if result["overall_status"] == "PASS" else 1
    except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        # Do not echo an arbitrary filename, token, exception or sample content.
        print("BLOCK: invalid/changed synthetic kit or inaccessible report destination.", file=sys.stderr)
        return 2
    except Exception:
        print("BLOCK: unexpected scanner error (details deliberately withheld).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
