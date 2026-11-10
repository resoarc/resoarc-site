"""Create synthetic, non-executable review inputs for Security Trio.

Use: py -3 review-kit/generate_samples.py --output C:\Temp\SecurityTrioReview
No network, third-party modules, real secrets, customer logs or malware.
An existing output path is never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

SAMPLES = (
    "secret-review.env",
    "secret-placeholder.env",
    "archive-review.zip",
    "access-review.log",
    "normal-access.log",
    "pdf-marker-review.pdf",
    "mismatch-review.pdf",
    "double-extension.pdf.exe",
    "plain-review.txt",
)


def create_samples(target: Path) -> dict:
    """Create all files atomically with respect to the target directory name."""
    if target.is_symlink() or target.exists():
        raise FileExistsError("BLOCK: output already exists; choose a NEW empty path")
    # Refuse placing generated mock inputs inside the source tree, where they
    # could be committed accidentally or mistaken for production samples.
    source_root = Path(__file__).resolve().parents[1]
    resolved = target.resolve(strict=False)
    if resolved == source_root or source_root in resolved.parents:
        raise ValueError("BLOCK: choose a directory outside apps/security-trio")
    target.mkdir(parents=True, exist_ok=False)
    # Deliberately fabricated, not a credential for any real service.
    fake_value = "".join(("Demo", "Only", "Not", "Real", "42"))
    (target / "secret-review.env").write_text(
        "database_password=" + fake_value + "\n", encoding="utf-8"
    )
    (target / "secret-placeholder.env").write_text(
        "database_password=YOUR_PASSWORD_HERE\n", encoding="utf-8"
    )
    with zipfile.ZipFile(target / "archive-review.zip", "w") as zf:
        zf.writestr("settings/sample.env", "api_key=" + fake_value)
        # A path traversal *name*, never extracted or executed.
        zf.writestr("../escape.txt", "harmless synthetic archive member")
    def line(ip: str, time: str, path: str, status: int) -> str:
        return (
            f'{ip} - - [{time} +0900] "GET {path} HTTP/1.1" '
            f'{status} 123 "-" "SecurityTrioReviewKit"\n'
        )
    timestamp = "10/Nov/2026:09:00:00"
    log = [
        line("198.51.100.12", timestamp, "/.env", 404),
        line("198.51.100.12", timestamp,
             "/health?access_token=" + "".join(("Demo", "Query", "Should", "Hide", "55")), 200),
    ]
    log += [
        line("198.51.100.12", timestamp, f"/missing{i}", 404)
        for i in range(13)
    ]
    (target / "access-review.log").write_text("".join(log), encoding="utf-8")
    (target / "normal-access.log").write_text(
        line("203.0.113.9", timestamp, "/health", 200), encoding="utf-8"
    )
    # These are intentionally minimal INERT byte-pattern fixtures, NOT valid PDFs.
    (target / "pdf-marker-review.pdf").write_bytes(b"%PDF-1.7\n/JavaScript /OpenAction\n%%EOF\n")
    (target / "mismatch-review.pdf").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"synthetic type-mismatch sample\n"
    )
    # Contains no PE header or executable code. DO NOT run this text-only fixture.
    (target / "double-extension.pdf.exe").write_bytes(
        b"TEXT ONLY: fake double-extension review sample; NOT AN EXECUTABLE.\n"
    )
    (target / "plain-review.txt").write_text(
        "Harmless sample: no threat detection is expected.\n", encoding="utf-8"
    )
    digests = {
        name: hashlib.sha256((target / name).read_bytes()).hexdigest()
        for name in SAMPLES
    }
    manifest = {
        "schema_version": 1,
        "type": "SYNTHETIC_LOCAL_REVIEW_ONLY",
        "warning": "No malware or real secrets. Minimal PDF markers are not valid documents.",
        "files_sha256": digests,
        "expected": {
            "secret-review.env": "Secret Scout: 機密値を含む設定; never print mock value",
            "secret-placeholder.env": "Secret Scout: no secret finding",
            "archive-review.zip": "Secret Scout: mock secret and ZIP内の危険なパス; no extraction",
            "access-review.log": "Log Lantern: 秘密-related probe and 404 burst; query and source IP redacted",
            "normal-access.log": "Log Lantern: one clean request",
            "pdf-marker-review.pdf": "File Inspector: PDFに能動的な構造の兆候",
            "mismatch-review.pdf": "File Inspector: 拡張子と実形式が不一致",
            "double-extension.pdf.exe": "File Inspector: 二重拡張子 (not a real EXE; never run)",
            "plain-review.txt": "File Inspector: no finding",
        },
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="NEW output directory OUTSIDE the Security Trio source tree")
    args = parser.parse_args()
    try:
        manifest = create_samples(args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"BLOCK: {exc}\n")
    print(f"Created {len(manifest['files_sha256'])} synthetic files: {args.output}")
    print("Use manifest.json for hashes and expected behavior. Never run *.exe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
