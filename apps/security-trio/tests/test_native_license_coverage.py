"""Negative tests for frozen Windows native-license coverage gate."""
from __future__ import annotations

import copy
import unittest

from audit_license_coverage import (
    ALL_NOTICES, BINS, required_notices_for_native, verify_coverage,
)

SAMPLE = [
    "python312.dll", "_bz2.pyd", "_lzma.pyd", "_decimal.pyd",
    "_hashlib.pyd", "_tkinter.pyd", "libcrypto-3.dll", "zlib1.dll",
    "tcl86t.dll", "tk86t.dll", "VCRUNTIME140.dll",
    "api-ms-win-core-console-l1-1-0.dll",
    r"tkinterdnd2\tkdnd\win-x64\libtkdnd2.9.4.dll",
]
NAMES = {f"third_party_licenses/{name}" for name in ALL_NOTICES}
NAMES.update(BINS)
NAMES.update(("SHA256SUMS.txt", "LICENSE.txt", "THIRD_PARTY_NOTICES.md"))


def inventory():
    return {"applications": [
        {
            "binary": name,
            "native_runtime_members": SAMPLE[:],
            "foreign_platform_tkdnd_members": [],
        }
        for name in BINS
    ]}


class NativeLicenseCoverageTests(unittest.TestCase):
    def test_complete_inventory_is_accepted(self):
        result = verify_coverage(inventory(), set(NAMES))
        self.assertEqual(result["third_party_notice_files"], len(ALL_NOTICES))

    def test_unknown_native_binary_blocks_distribution(self):
        data = inventory()
        for a in data["applications"]:
            a["native_runtime_members"].append("suspicious-dependency.dll")
        with self.assertRaisesRegex(ValueError, "unknown native library"):
            verify_coverage(data, set(NAMES))

    def test_foreign_platform_tkdnd_is_blocked(self):
        data = inventory()
        data["applications"][1]["foreign_platform_tkdnd_members"] = ["tkdnd/linux-x64/libtkdnd.so"]
        with self.assertRaisesRegex(ValueError, "cross-platform"):
            verify_coverage(data, set(NAMES))

    def test_missing_third_party_license_is_blocked(self):
        missing = set(NAMES) - {"third_party_licenses/OpenSSL-3-LICENSE.txt"}
        with self.assertRaisesRegex(ValueError, "missing, unexpected or outdated"):
            verify_coverage(inventory(), missing)

    def test_unexpected_old_license_is_blocked(self):
        extra = set(NAMES) | {"third_party_licenses/OpenSSL-1.1.1-LICENSE.txt"}
        with self.assertRaisesRegex(ValueError, "missing, unexpected or outdated"):
            verify_coverage(inventory(), extra)

    def test_missing_own_mit_license_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "distribution ZIP missing"):
            verify_coverage(inventory(), set(NAMES) - {"LICENSE.txt"})

    def test_mismatched_three_exe_payloads_are_blocked(self):
        data = inventory()
        data["applications"][2]["native_runtime_members"].remove("libcrypto-3.dll")
        with self.assertRaisesRegex(ValueError, "inconsistent native components"):
            verify_coverage(data, set(NAMES))

    def test_unsupported_cpu_variant_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "unreviewed native binary path"):
            required_notices_for_native(r"tkinterdnd2\tkdnd\win-arm64\libtkdnd.dll")


if __name__ == "__main__":
    unittest.main()
