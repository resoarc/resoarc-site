#!/usr/bin/env python3
"""Verify published software-license identity for OpenSSF OSPS-LE-02.02.

This validates an evidence ledger against the pinned 35-asset release inventory.
It is a reproducible license-identity check, NOT legal advice, a copyright
ownership certification, or a substitute for maintainer approval of new code.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSES = ROOT / "docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json"
EVIDENCE = ROOT / "docs/compliance/OSPS_LE02_35_SOFTWARE_LICENSE_EVIDENCE_20261106.json"
CATALOG = ROOT / "site/downloads/index.html"
NOTICES = ROOT / "site/downloads/THIRD_PARTY_LICENSES.md"
# Intentionally restricted to upstream software licenses observed in the
# identified release assets, not a generic declaration about arbitrary licenses.
ACCEPTED_SOFTWARE_SPDX = {"MIT", "Apache-2.0"}


def verify():
    errors = []
    pins = json.loads(LICENSES.read_text(encoding="utf8"))
    docs = json.loads(EVIDENCE.read_text(encoding="utf8"))
    names = {x["asset"]: x for x in pins["packages"]}
    records = docs["records"]
    by_name = {x["asset"]: x for x in records}
    if len(names) != 35 or len(records) != 35 or len(by_name) != 35 or names.keys() != by_name.keys():
        errors.append("35 release ZIP files must be uniquely included in the approved license ledger")
    if docs.get("software_licenses_found") != ["MIT", "Apache-2.0"]:
        errors.append("approved software license inventory changed")
    if docs.get("copyright_permission_legal_signoff") != "NOT_PERFORMED":
        errors.append("do not imply copyright legal signoff without a separate real review")
    if docs.get("source_zip_license_count") != 13 or docs.get("signed_zip_companion_count") != 22:
        errors.append("source ZIP / signed ZIP license mechanisms have changed")
    if any(not x.get("software_license_definition_supported") for x in records):
        errors.append("at least one release software license is not supported by OSI/FSF evidence")

    catalog = CATALOG.read_text(encoding="utf8")
    thirdparty = NOTICES.read_text(encoding="utf8")
    for name, row in by_name.items():
        pin = names[name]
        if row["sha256"] != pin["sha256"] or row["bytes"] != pin["bytes"]:
            errors.append(f"release digest changed for {name}")
        if row["released_software_license_spdx"] != "MIT":
            errors.append(f"primary software license must be reviewed: {name}")
        if row.get("license_definition") != "OSI":
            errors.append(f"unverified software license definition: {name}")
        if row["companion_license_url"] != "https://resoarc.com/downloads/LICENSE":
            errors.append(f"missing distribution sidecar: {name}")
        if row["companion_mit_sha256"] != docs["records"][0]["companion_mit_sha256"]:
            errors.append(f"MIT companion digest mismatch for {name}")
        if row.get("independent_author_copyright_permission_verified") is not False:
            errors.append(f"false independent author verification flag: {name}")
        if catalog.count('href="/downloads/' + name + '"') != 1:
            errors.append(f"download is not linked exactly once: {name}")
        if pin["signed_installer"]:
            if row["license_evidence_type"] != "unchanged-signed-archive-external-companion" or row["embedded_full_mit_documents"]:
                errors.append(f"signed release sidecar mechanism inconsistent: {name}")
        elif row["license_evidence_type"] != "embedded-full-mit-text" or not row["embedded_full_mit_documents"]:
            errors.append(f"source ZIP missing MIT text proof: {name}")
        for doc in row["embedded_full_mit_documents"]:
            if doc.get("spdx") != "MIT" or len(doc.get("sha256", "")) != 64:
                errors.append(f"invalid embedded MIT proof: {name}")
        for item in row.get("additional_components", []):
            for license_id in item["license_ids"]:
                if item["category"] == "software" and license_id not in ACCEPTED_SOFTWARE_SPDX:
                    errors.append(f"non-OSI/FSF software license: {name} {license_id}")
            if item["category"] != "software" and "not-software" not in item["category"] and "media-" not in item["category"]:
                errors.append(f"nonsoftware exception requires review: {name}")

    for token in ("fflate 0.8.3", "Apache License 2.0", "OFL", "Unsplash"):
        if token not in thirdparty:
            errors.append(f"third party notice missing: {token}")

    print("LE-02.02 evidence:", len(records), "ZIPs,", docs["source_zip_license_count"],
          "source MIT texts,", docs["signed_zip_companion_count"],
          "signed MIT companions; software licenses MIT and Apache-2.0.")
    print("Copyright/redistribution authority is NOT independently certified by this test.")
    for err in errors:
        print("ERROR:", err, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(verify())
