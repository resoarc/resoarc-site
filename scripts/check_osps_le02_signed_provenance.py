#!/usr/bin/env python3
"""Cross-check signed asset provenance against the publicly audited 35-release manifest.

This is a source and rights-evidence **completeness** check. It does not issue
human legal approval, decide ownership, or automatically mark LE-02.02 Met.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/compliance/OSPS_LE02_SIGNED22_PROVENANCE_REVIEW_20261106.json"
LICENSES = ROOT / "docs/compliance/OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json"


def run():
    errors = []
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    licenses = json.loads(LICENSES.read_text(encoding="utf-8"))
    pkg = {x["asset"]: x for x in licenses["packages"]}
    reports = evidence.get("records", [])
    signed = {name for name, item in pkg.items() if item["signed_installer"]}
    if len(pkg) != 35 or len(signed) != 22:
        errors.append("Release manifest must contain 35 assets, 22 signed")
    if len(reports) != 22 or {x["asset"] for x in reports} != signed:
        errors.append("LE-02 report does not cover every signed release exactly once")
    if evidence.get("independent_rights_clearance") is not False:
        errors.append("Machine evidence cannot claim independent legal clearance")
    pub = {"FULL": 0, "PARTIAL": 0, "NONE": 0}
    qa = {"FULL": 0, "PARTIAL": 0, "NO_CANDIDATE": 0}
    formal = 0
    for x in reports:
        name = x["asset"]
        n = x["public_git_total_files"]
        m = x["public_git_matched_files"]
        q = x["historical_qa_matched_files"]
        if not (0 <= m <= n and 0 <= q <= n and n > 0):
            errors.append("Invalid source-match count for "+name)
        expected_pub = "FULL" if m == n else "PARTIAL" if m > 0 else "NONE"
        expected_qa = "FULL" if q == n else "PARTIAL" if q > 0 else "NO_CANDIDATE"
        if x["public_git_source_status"] != expected_pub or x["historical_qa_source_status"] != expected_qa:
            errors.append("Source-match label and count conflict for "+name)
        if x.get("author_rights_verification") != "NOT_INDEPENDENTLY_VERIFIED":
            errors.append("Unsupported legal claim in "+name)
        if x.get("source_approval_record") != "OWNER_REVIEW_REQUIRED":
            errors.append("Owner approval cannot be faked for "+name)
        pub[x["public_git_source_status"]] += 1
        qa[x["historical_qa_source_status"]] += 1
        formal += bool(x.get("prior_central_release_manifest"))
    if pub != {"FULL": 8, "PARTIAL": 4, "NONE": 10}:
        errors.append("Unexpected public Git correspondence breakdown "+str(pub))
    if qa != {"FULL": 12, "PARTIAL": 6, "NO_CANDIDATE": 4}:
        errors.append("Unexpected historical QA match breakdown "+str(qa))
    if formal != 8:
        errors.append("Formal historical release count differs from 8")
    print("OSPS LE-02 provenance audit: signed",len(reports),"Git",pub,"QA",qa,"formal",formal)
    for e in errors:
        print("FAIL:",e,file=sys.stderr)
    print("LEGAL STATUS: HOLD; a code match or old release approval is not a human rights attestation")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(run())
