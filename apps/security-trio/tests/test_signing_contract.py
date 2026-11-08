"""Offline checks for the unsigned-to-signed Security Trio release contract.

These tests do not claim actual SignPath enrollment, approval, signature validity
or issuance. They validate the files submitted to the human enrollment review.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
NS = "{http://signpath.io/artifact-configuration/v1}"
EXES = ("ResoArcSecretScout.exe", "ResoArcLogLantern.exe", "ResoArcFileInspector.exe")
ACTION = re.compile(r"\buses:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([^\s#]+)")


class SigningContractTests(unittest.TestCase):
    def test_signpath_artifact_signs_exactly_three_own_binaries(self):
        config = ET.parse(ROOT / "signpath" / "artifact-configuration.xml").getroot()
        self.assertEqual(config.tag, NS + "artifact-configuration")
        children = list(config)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].tag, NS + "zip-file")
        entries = list(children[0])
        self.assertEqual(len(entries), 3)
        self.assertCountEqual([x.attrib.get("path") for x in entries], EXES)
        for element in entries:
            self.assertEqual(element.tag, NS + "pe-file")
            self.assertEqual(element.attrib.get("product-name"), "ResoArc Security Trio")
            self.assertEqual(element.attrib.get("product-version"), "0.3.0.4")
            self.assertEqual(element.attrib.get("file-version"), "0.3.0.4")
            self.assertEqual(element.attrib.get("company-name"), "ResoArc")
            self.assertEqual(element.attrib.get("original-filename"), element.attrib.get("path"))
            self.assertEqual([x.tag for x in element], [NS + "authenticode-sign"])

    def test_pe_metadata_is_consistent_across_three_apps(self):
        for exe in EXES:
            with self.subTest(exe=exe):
                text = (ROOT / "metadata" / (exe[:-4] + ".txt")).read_text(encoding="utf-8")
                for needle in (
                    "'ResoArc Security Trio'", "'0.3.0.4'",
                    "'" + exe + "'", "'ResoArc'",
                ):
                    self.assertIn(needle, text)

    def test_ci_actions_are_pinned_to_full_commits(self):
        for name in ("security-trio-windows.yml", "security-trio-signpath.yml"):
            data = (REPO / ".github" / "workflows" / name).read_text(encoding="utf-8")
            entries = ACTION.findall(data)
            self.assertGreaterEqual(len(entries), 3)
            for action, ref in entries:
                with self.subTest(workflow=name, action=action):
                    self.assertRegex(ref, r"^[0-9a-f]{40}$")

    def test_signing_entrypoint_requires_manual_release_barriers(self):
        data = (REPO / ".github" / "workflows" / "security-trio-signpath.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", data)
        self.assertNotIn("pull_request:", data)
        self.assertIn("environment: signpath-approved", data)
        self.assertIn("refs/heads/release/security-trio-", data)
        self.assertIn("SIGNPATH_ARTIFACT_CONFIGURATION_SLUG", data)
        self.assertIn("SIGNPATH_SIGNER_SHA1_THUMBPRINT", data)
        self.assertIn("SIGNPATH_API_TOKEN", data)
        self.assertIn("verify_signed_release.ps1", data)
        self.assertIn("wait-for-completion-timeout-in-seconds:", data)

    def test_signature_gate_is_fail_closed_for_unsigned_exes(self):
        data = (ROOT / "verify_signed_release.ps1").read_text(encoding="utf-8")
        for required in (
            "Get-AuthenticodeSignature", "BLOCK:", "TimeStamperCertificate",
            "EnhancedKeyUsageList", "ExpectedCertificateThumbprint", "SHA256",
        ):
            self.assertIn(required, data)
        self.assertNotIn("Set-AuthenticodeSignature", data)

    def test_public_policy_does_not_claim_approval(self):
        data = (ROOT / "CODE_SIGNING_POLICY.md").read_text(encoding="utf-8")
        for marker in ("未署名", "未完了", "SignPath Foundation", "manual"):
            self.assertIn(marker.lower(), data.lower())


if __name__ == "__main__":
    unittest.main()
