#!/usr/bin/env python3
"""Build a NON-PUBLIC, unsigned Guardian test candidate. Never creates a GitHub release."""
import argparse,hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
TARGETS=(("linux","amd64"),("linux","arm64"),("windows","amd64"))
NOTICE="""TRAPNET GUARDIAN: UNSIGNED CI CANDIDATE ONLY. NOT FOR PUBLIC INSTALLATION.
Requires offline-root-signed signer policy and an independently verified
SHA-256 fingerprint of the binary Root public key (-root-sha256).
Do not obtain this fingerprint from the same untrusted feed/bundle.
No installer, automatic updater, signing key, feed public key or network blocking
is bundled. SHA-256 is a change detector, NOT publisher authentication. A
separate human security review, signature and recovery plan are still required.
"""
def sha(data):return hashlib.sha256(data).hexdigest()
def build(source,out):
    source=Path(source).resolve();out=Path(out).resolve()
    if not (source/"go.mod").is_file():raise ValueError("missing Go module")
    if out.exists():raise ValueError("refuse to overwrite an existing candidate directory")
    out.mkdir(mode=0o700,parents=True)
    items=[]
    for platform,arch in TARGETS:
        name="guardian-"+platform+"-"+arch+(".exe" if platform=="windows" else "")
        env=dict(os.environ,GOOS=platform,GOARCH=arch,CGO_ENABLED="0")
        r=subprocess.run(["go","build","-trimpath","-buildvcs=false","-ldflags=-X main.requireRootPolicy=true","-o",str(out/name),"./cmd/guardian"],
                         cwd=source,env=env,capture_output=True,text=True,timeout=120)
        if r.returncode:raise ValueError("build failed: "+platform+"/"+arch)
        content=(out/name).read_bytes()
        items.append({"file":name,"os":platform,"arch":arch,"sha256":sha(content),"bytes":len(content)})
    manifest={"schema":"trapnet.unsigned-guardian-ci.v1","public_release":False,
              "signed":False,"automatic_update":False,"auto_blocking":False, "root_signer_policy_required":True,"builds":items}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    (out/"READ_ME_FIRST.txt").write_text(NOTICE)
    dest=out/"guardian-UNSIGNED-CI-ONLY.zip"
    with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for path in sorted(out.iterdir()):
            if path==dest:continue
            info=zipfile.ZipInfo(path.name,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            z.writestr(info,path.read_bytes())
    (out/"ZIP_SHA256.txt").write_text(sha(dest.read_bytes())+"  "+dest.name+"\n")
    return manifest
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",default=".");p.add_argument("--out",required=True);a=p.parse_args()
    try:print(json.dumps(build(a.source,a.out),indent=2))
    except Exception as e:print("candidate refused: "+type(e).__name__,file=sys.stderr);sys.exit(1)
