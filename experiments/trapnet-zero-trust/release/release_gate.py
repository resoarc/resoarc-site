#!/usr/bin/env python3
"""Fail-closed review of Guardian public-beta evidence. Never signs or publishes."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

REQUIREMENTS = {
 "source_revision_pinned":"Exact source SHA and security review",
 "ci_go_and_security_green":"Go race/vet, build and CLI acceptance at exact source revision",
 "binary_origin_attested":"Independently verified source-to-binary provenance",
 "distributable_signature_verified":"Publisher signature and pinned release key verified",
 "installer_uninstaller_tested":"Install, removal and rollback on supported OS",
 "feed_signer_custody_and_rotation":"Offline key custody and emergency revocation",
 "no_remote_control_reviewed":"No automatic blocking, execution or telemetry",
 "incident_response_and_stop":"Emergency stop and recovery exercise",
 "privacy_terms_and_contact_reviewed":"Privacy notice and security contact",
 "independent_security_review":"Independent review of exact beta candidate",
 "release_manager_approval":"Named release authority approved exact candidate digest"
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

def evidence_reference(value):
    if not isinstance(value,str) or len(value)>800 or any(c.isspace() for c in value):
        return False
    try: url=urlsplit(value)
    except ValueError: return False
    return url.scheme=="https" and bool(url.hostname) and bool(url.path.strip("/")) and not url.username and not url.password

def assess(data):
    data=data if isinstance(data,dict) else {}
    commit=data.get("source_commit_sha")
    candidate=data.get("candidate_sha256")
    pinned=(isinstance(commit,str) and bool(HEX40.fullmatch(commit))
            and isinstance(candidate,str) and bool(HEX64.fullmatch(candidate)))
    checks=data.get("checks",{})
    checks=checks if isinstance(checks,dict) else {}
    missing=[]
    for key,requirement in REQUIREMENTS.items():
        item=checks.get(key)
        passed=(pinned and isinstance(item,dict) and item.get("passed") is True
                and evidence_reference(item.get("evidence"))
                and item.get("source_commit_sha")==commit
                and item.get("candidate_sha256")==candidate)
        if not passed:missing.append({"id":key,"requirement":requirement})
    return {"schema":"trapnet.guardian-beta-gate.v2","identity_pins_valid":bool(pinned),
            "source_commit_sha":commit if pinned else None,
            "candidate_sha256":candidate if pinned else None,
            "ready_for_human_decision":bool(pinned and not missing),
            "publication_executed":False,"required":len(REQUIREMENTS),
            "complete":len(REQUIREMENTS)-len(missing),"missing":missing,
            "limitation":"Checks only evidence shape/revision consistency. A human must verify links, signatures, custody, independence and provenance."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True)
    p.add_argument("--out")
    args=p.parse_args()
    try:
        result=assess(json.loads(Path(args.evidence).read_text(encoding="utf-8")))
        raw=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
        if args.out:
            output=Path(args.out)
            if output.is_symlink() or output.exists():raise ValueError("Refusing replacement of previous gate evidence")
            with output.open("x",encoding="utf-8") as f:f.write(raw)
        print(raw,end="")
        return 0 if result["ready_for_human_decision"] else 3
    except (OSError,ValueError,TypeError) as exc:
        print("beta release gate refused:",type(exc).__name__,file=sys.stderr)
        return 2

if __name__=="__main__":sys.exit(main())
