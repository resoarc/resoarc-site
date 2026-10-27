#!/usr/bin/env python3
"""Read-only Sonar runtime-source parity. Result belongs in PRIVATE ops records.

An inventory created by the same machine is not provenance. Compare against a
manifest approved and independently stored before deploying, never an
auto-regenerated manifest from the machine under review.
"""
import argparse,hashlib,json,sys
from pathlib import Path

FILES={"web/decoy.py","web/decoy_expansion.py","web/sonar_profiles.py",
       "bin/sonar_hardening.py","bin/sonar_snapshot.py"}

def inventory(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError("invalid source root")
    checks={}
    for rel in sorted(FILES):
        file=root/rel
        if file.is_symlink() or not file.is_file():raise ValueError("missing or symlinked source")
        if file.stat().st_size>2*1024*1024:raise ValueError("oversized source file")
        b=file.read_bytes()
        checks[rel]={"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)}
    return {"schema":"trapnet.sonar-private-parity.v1","files":checks,"self_attestation":False}

def compare(pinned,measured):
    if pinned.get("schema")!="trapnet.sonar-private-parity.v1" or set(pinned.get("files",{}))!=FILES:
        raise ValueError("expected manifest has wrong schema or file list")
    difference=[rel for rel in sorted(FILES) if pinned["files"][rel]!=measured["files"][rel]]
    return {"schema":"trapnet.sonar-parity-verdict.v1","matches_pinned_inventory":not difference,
            "difference_paths":difference,"source_provenance_verified":False,
            "no_public_private_node_data":True}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",required=True)
    p.add_argument("--compare",help="separately approved private manifest");p.add_argument("--out")
    a=p.parse_args()
    try:
        actual=inventory(a.root)
        result=compare(json.loads(Path(a.compare).read_text()),actual) if a.compare else actual
        raw=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if a.out:
            path=Path(a.out)
            if path.is_symlink() or path.exists():raise ValueError("refuse overwriting previous evidence")
            with path.open("x") as f:f.write(raw)
            path.chmod(0o600)
        else:print(raw,end="")
        if a.compare and not result["matches_pinned_inventory"]:sys.exit(3)
    except Exception as e:
        print("parity refused: "+type(e).__name__,file=sys.stderr);sys.exit(2)
