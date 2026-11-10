"""Tests for signed *candidate packaging mechanics*, not fake signature issuance.

Synthetic files are NOT SIGNED. Only Windows Authenticode validation can make
the real release gate succeed, and these tests never mock that gate as valid.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from package_signed_candidate import checked_signed_inputs, signing_evidence, EXACT_NAMES, BINARIES, ROOT

ENV = {
    "EXPECTED_SIGNER_THUMBPRINT": "a" * 40,
    "SIGNPATH_SIGNING_REQUEST_ID": "synthetic-review-only",
    "SIGNPATH_SIGNING_REQUEST_URL": "https://app.signpath.io/Web/signingrequests/synthetic",
    "GITHUB_SHA": "b" * 40,
    "GITHUB_RUN_ID": "123456",
}


class SignedCandidatePolicyTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        self.hashes = {}
        for name in BINARIES:
            fake = b"NOT A SIGNED EXECUTABLE; FIXTURE: " + name.encode("ascii")
            (self.root / name).write_bytes(fake)
            self.hashes[name] = hashlib.sha256(fake).hexdigest()
        (self.root / "SHA256SUMS.txt").write_text(
            "".join(f"{self.hashes[n]}  {n}\n" for n in BINARIES),
            encoding="ascii",
        )

    def test_synthetic_manifest_parsing_only(self):
        # This routine validates hashes, NOT Authenticode. It is NOT signing proof.
        self.assertEqual(checked_signed_inputs(self.root), self.hashes)

    def test_mismatch_is_blocked(self):
        (self.root / BINARIES[0]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            checked_signed_inputs(self.root)

    def test_unexpected_file_is_blocked(self):
        (self.root / "unexpected.dll").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "unexpected files"):
            checked_signed_inputs(self.root)

    def test_missing_manifest_is_blocked(self):
        (self.root / "SHA256SUMS.txt").unlink()
        with self.assertRaisesRegex(ValueError, "unexpected files"):
            checked_signed_inputs(self.root)

    def test_duplicate_manifest_entries_are_blocked(self):
        with (self.root / "SHA256SUMS.txt").open("a", encoding="ascii") as fd:
            fd.write(f"{self.hashes[BINARIES[0]]}  {BINARIES[0]}\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            checked_signed_inputs(self.root)

    def test_crlf_is_accepted_without_hash_changes(self):
        path = self.root / "SHA256SUMS.txt"
        path.write_bytes("".join(f"{self.hashes[name]}  {name}\r\n" for name in BINARIES).encode("ascii"))
        self.assertEqual(checked_signed_inputs(self.root), self.hashes)

    def test_real_signing_request_metadata_is_required(self):
        with patch.dict(os.environ, ENV, clear=True):
            e = signing_evidence()
        self.assertEqual(e["status"], "SIGNED_CANDIDATE_NOT_PUBLISHED")
        self.assertEqual(e["human_release_approval"], "PENDING")

    def test_refuse_non_signpath_request_url(self):
        values = dict(ENV, SIGNPATH_SIGNING_REQUEST_URL="https://evil.example/path")
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(ValueError, "trusted SignPath"):
                signing_evidence()

    def test_refuse_missing_request_id(self):
        values = dict(ENV, SIGNPATH_SIGNING_REQUEST_ID="")
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(ValueError, "request ID"):
                signing_evidence()

    def test_refuse_unknown_thumbprint(self):
        values = dict(ENV, EXPECTED_SIGNER_THUMBPRINT="not-approved")
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(ValueError, "fingerprint absent"):
                signing_evidence()

    def test_signing_workflow_requires_post_signature_package_step(self):
        data = (ROOT.parents[1] / ".github" / "workflows" / "security-trio-signpath.yml").read_text(
            encoding="utf-8"
        )
        expected_order = [
            "id: signpath_request",
            "verify_signed_release.ps1",
            "run: python package_signed_candidate.py",
            "SecurityTrio-SIGNED-candidate-with-licenses-not-published",
        ]
        indexes = [data.index(token) for token in expected_order]
        self.assertEqual(indexes, sorted(indexes))
        for field in (
            "steps.signpath_request.outputs.signing-request-id",
            "steps.signpath_request.outputs.signing-request-web-url",
            "SIGNPATH_SIGNER_SHA1_THUMBPRINT",
            "environment: signpath-approved",
        ):
            self.assertIn(field, data)


if __name__ == "__main__":
    unittest.main()
