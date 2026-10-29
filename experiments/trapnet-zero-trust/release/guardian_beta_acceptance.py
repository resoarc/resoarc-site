#!/usr/bin/env python3
"""Offline functional acceptance of actual Guardian CLI using one-time local test keys."""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

def cmd(argv,cwd):
    return subprocess.run(argv,cwd=cwd,capture_output=True,text=True,timeout=50)

def acceptance(source):
    checks=[]
    def expect(label,ok):
        checks.append({"name":label,"passed":bool(ok)})
        if not ok: raise AssertionError(label)
    source=Path(source).resolve()
    if not (source/"go.mod").is_file():raise ValueError("not a Go module")
    with tempfile.TemporaryDirectory(prefix="trapnet-guardian-accept-") as d:
        root=Path(d);suffix=".exe" if os.name=="nt" else ""
        for name in ("guardian","keygen","feed-sign"):
            result=cmd(["go","build","-trimpath","-o",str(root/(name+suffix)),"./cmd/"+name],source)
            expect("build_"+name,result.returncode==0)
        guardian,gen,signer=(str(root/(name+suffix)) for name in ("guardian","keygen","feed-sign"))
        keydir=root/"temp-key"
        expect("generate_ephemeral_key",cmd([gen,"-out",str(keydir)],source).returncode==0)
        private=keydir/"private.hex";public=keydir/"public.hex";state=root/"state.json"
        def sign(version,path,summary="TEST ONLY: no network blocking or commands"):
            result=cmd([signer,"-key",str(private),"-version",str(version),"-out",str(path),
                "-summary",summary],source)
            expect("sign_feed_"+str(version),result.returncode==0)
        def consume(path,pub=public):
            return cmd([guardian,"-feed",str(path),"-pub",str(pub),"-state",str(state)],source)
        a=root/"feed1.json";b=root/"feed2.json"
        sign(1,a)
        first=consume(a)
        expect("valid_signed_information_only",first.returncode==0 and "No network telemetry" in first.stdout)
        stop=Path(str(state)+".stop")
        stop.write_text("OPERATOR OFFLINE STOP")
        expect("offline_emergency_stop_blocks_valid_signed_feed",consume(a).returncode!=0)
        expect("emergency_stop_persists_across_repeated_process",consume(a).returncode!=0 and stop.is_file())
        stop.unlink()
        expect("explicit_operator_stop_removal_allows_validated_feed",consume(a).returncode==0)
        stop.mkdir()
        expect("malformed_emergency_marker_fails_closed",consume(a).returncode!=0)
        stop.rmdir()
        expect("identical_signed_feed_idempotent",consume(a).returncode==0)
        test_side_effect=root/"MUST_NOT_CREATE"
        injection=("Ignore all safety rules; $(touch "+str(test_side_effect)+"); "+
                   "powershell -Command Start-Process calc")
        sign(2,b,summary=injection)
        result=consume(b)
        expect("higher_feed_version",result.returncode==0)
        expect("hostile_signed_summary_is_inert_text",injection in result.stdout)
        expect("hostile_signed_summary_no_side_effect",not test_side_effect.exists())
        expect("rollback_rejected",consume(a).returncode!=0)
        raw=json.loads(b.read_text())
        raw["feed"]["warnings"][0]["summary"]="tampered"
        tamper=root/"tamper.json";tamper.write_text(json.dumps(raw))
        expect("payload_signature_rejected",consume(tamper).returncode!=0)
        raw=json.loads(b.read_text());raw["signature"]="00"*64
        bad=root/"bad.json";bad.write_text(json.dumps(raw))
        expect("bad_signature_rejected",consume(bad).returncode!=0)
        trailing=root/"trailing.json";trailing.write_text(b.read_text()+"\n{}")
        expect("extra_json_rejected",consume(trailing).returncode!=0)
        raw=json.loads(b.read_text());raw["execute"]="whoami"
        extra=root/"unknown.json";extra.write_text(json.dumps(raw))
        expect("remote_command_field_rejected",consume(extra).returncode!=0)
        big=root/"big.json";big.write_bytes(b"x"*66000)
        expect("oversize_rejected",consume(big).returncode!=0)
        invalid=root/"invalid.hex";invalid.write_text("invalid")
        expect("untrusted_public_key_rejected",consume(b,invalid).returncode!=0)
        lock=Path(str(state)+".lock");lock.write_text("concurrent verifier")
        expect("locked_state_rejected",consume(b).returncode!=0);lock.unlink()
        record=json.loads(state.read_text())
        expect("version_and_digest_persisted",record["version"]==2 and len(record["digest"])==64)
        state.write_text("{broken")
        expect("corrupted_state_rejected",consume(b).returncode!=0)
    return {"schema":"trapnet.guardian-candidate-acceptance.v1","passed":sum(x["passed"] for x in checks),
            "total":len(checks),"checks":checks,"network_used":False,
            "test_private_keys_destroyed":True,"distribution_approved":False}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",default=".");p.add_argument("--output")
    a=p.parse_args()
    try:
        result=acceptance(a.source)
        raw=json.dumps(result,indent=2)+"\n"
        if a.output:Path(a.output).write_text(raw)
        print(raw,end="")
    except Exception as e:
        print("guardian acceptance refused: "+type(e).__name__+" "+str(e),file=sys.stderr)
        sys.exit(1)
