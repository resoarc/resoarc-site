#!/usr/bin/env python3
"""Fail-closed Guardian public-beta evidence checklist. This tool cannot publish a release."""
import argparse,json,sys
from pathlib import Path

REQUIREMENTS={
 "source_revision_pinned":"Exact source SHA and source security review",
 "ci_go_and_security_green":"Race/vet, cross-build and CLI acceptance green on exact commit",
 "binary_origin_attested":"Verifiable source-to-binary provenance",
 "distributable_signature_verified":"Detached binary signatures from separate release key verified",
 "installer_uninstaller_tested":"Documented install, remove and rollback on each target OS",
 "feed_signer_custody_and_rotation":"Offline feed key custody, compromise response and rotation",
 "no_remote_control_reviewed":"Verify no auto-block, arbitrary commands or forced telemetry",
 "incident_response_and_stop":"Operational emergency halt and recovery exercise",
 "privacy_terms_and_contact_reviewed":"Privacy notice and vulnerability contact",
 "independent_security_review":"Independent security review of the approved beta scope",
 "release_manager_approval":"Explicit named release authority approves exact candidate digest"
}
def assess(evidence):
    checks=evidence.get("checks",{}) if isinstance(evidence,dict) else {}
    pending=[]
    for k,description in REQUIREMENTS.items():
        item=checks.get(k)
        if not (isinstance(item,dict) and item.get("passed") is True
                and isinstance(item.get("evidence"),str) and len(item["evidence"].strip())>=12):
            pending.append({"id":k,"requirement":description})
    return {"schema":"trapnet.guardian-beta-gate.v1","ready_for_human_decision":not pending,
            "publication_executed":False,"required":len(REQUIREMENTS),
            "complete":len(REQUIREMENTS)-len(pending),"missing":pending,
            "note":"Even a green assessment never publishes or signs an artifact."}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--evidence",required=True);p.add_argument("--out");a=p.parse_args()
    try:
        r=assess(json.loads(Path(a.evidence).read_text(encoding="utf-8")))
        data=json.dumps(r,ensure_ascii=False,indent=2)+"\n"
        if a.out:Path(a.out).write_text(data,encoding="utf-8")
        print(data,end="");sys.exit(0 if r["ready_for_human_decision"] else 3)
    except (OSError,ValueError,TypeError) as e:
        print("beta gate refused: "+type(e).__name__,file=sys.stderr);sys.exit(2)
