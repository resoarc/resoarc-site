#!/usr/bin/env python3
"""Native Guardian root policy acceptance: ephemeral keys only, no network."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

def run(args, cwd):
    return subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,text=True,timeout=40)
def acceptance(source):
    source=Path(source).resolve()
    checks=[]
    def check(name,ok):
        checks.append({"name":name,"passed":bool(ok)})
        if not ok:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="trapnet-root-policy-") as d:
        tmp=Path(d)
        suffix=".exe" if os.name=="nt" else ""
        exe={}
        for name in ("guardian","keygen","feed-sign","feed-policy-sign"):
            output=tmp/(name+suffix)
            argv=["go","build","-trimpath","-buildvcs=false"]
            if name=="guardian":argv+=["-ldflags=-X main.requireRootPolicy=true"]
            argv+=["-o",str(output),"./cmd/"+name]
            check("build_"+name,run(argv,source).returncode==0)
            exe[name]=output
        root=tmp/"root";old=tmp/"old";new=tmp/"new"
        for key in (root,old,new):
            check("generate_disposable_"+key.name,run([exe["keygen"],"-out",key],source).returncode==0)
        def issue_policy(version,allowed,filename):
            output=tmp/filename
            r=run([exe["feed-policy-sign"],"-root-key",root/"private.hex","-allowed-pubs",allowed/"public.hex",
                   "-version",str(version),"-out",output],source)
            check("issue_policy_"+str(version)+"_"+filename,r.returncode==0)
            return output
        def sign_feed(version,private,filename):
            output=tmp/filename
            r=run([exe["feed-sign"],"-key",private/"private.hex","-out",output,
                   "-version",str(version),"-summary","Synthetic offline warning, no network operation"],source)
            check("sign_feed_"+str(version)+"_"+filename,r.returncode==0)
            return output
        state=tmp/"guard-state.json"
        def consume(feed,policy=None,legacy=False):
            args=[exe["guardian"],"-feed",feed,"-state",state]
            if legacy: args+=["-pub",old/"public.hex"]
            else:args+=["-rootpub",root/"public.hex","-policy",policy]
            return run(args,source)
        p1=issue_policy(1,old,"p1.json");f1=sign_feed(1,old,"f1.json")
        r=consume(f1,p1)
        check("first_root_signed_feed_accepted",r.returncode==0 and "No network telemetry" in r.stdout)
        check("same_policy_and_feed_idempotent",consume(f1,p1).returncode==0)
        p2=issue_policy(2,new,"p2.json");f2=sign_feed(2,new,"f2.json")
        check("rotated_signer_feed_accepted",consume(f2,p2).returncode==0)
        f3=sign_feed(3,old,"f3-revoked.json")
        check("old_signer_revoked",consume(f3,p2).returncode!=0)
        check("old_root_policy_rollback_rejected",consume(f1,p1).returncode!=0)
        check("legacy_pub_mode_forbidden_in_beta_binary",consume(f1,legacy=True).returncode!=0)
        p2other=issue_policy(2,old,"p2-other.json")
        check("same_policy_version_equivocation_refused",consume(f3,p2other).returncode!=0)
        tampered=json.loads(p2.read_text())
        tampered["policy"]["version"]=3
        changed=tmp/"changed-policy.json";changed.write_text(json.dumps(tampered))
        check("tampered_root_signature_refused",consume(f2,changed).returncode!=0)
        record=json.loads(state.read_text())
        check("persisted_signer_policy_and_feed_version",record["policy_version"]==2 and
              record["version"]==2 and len(record["policy_digest"])==64)
    return {"schema":"trapnet.guardian-root-rotation-acceptance.v1",
            "passed":sum(c["passed"] for c in checks),"total":len(checks),
            "checks":checks,"temporary_keys_removed":True,"network_used":False,
            "public_release_approved":False}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--source",default=".")
    parser.add_argument("--output");args=parser.parse_args()
    try:
        result=acceptance(args.source)
        raw=json.dumps(result,indent=2)+"\n"
        if args.output:Path(args.output).write_text(raw)
        print(raw,end="")
    except Exception as err:
        print("Guardian root acceptance refused:",type(err).__name__,str(err),file=sys.stderr)
        sys.exit(1)
