#!/usr/bin/env python3
"""Offline import of consented existing Web/reverse-proxy logs, not a public listener.

This adapter intentionally DOES NOT auto-upload evidence or make verdicts.
Input may contain personal data: use only authorized logs on a protected host.
The output contains coarse counts only, with small cohorts suppressed.
"""
import argparse
import json
import os
import pathlib
import tempfile

from sonar_hardening import aggregate, input_lines

ALLOWED_SOURCES=("authorized_web_server","authorized_reverse_proxy")
SCHEMA="trapnet.passive-import.v0.1"

def process(source,kind,authorized=False):
    if not authorized:
        raise ValueError("explicit operator authorization is required")
    if kind not in ALLOWED_SOURCES:
        raise ValueError("unsupported source kind")
    result=aggregate(input_lines(source))
    result["adapter_schema"]=SCHEMA
    result["source_kind"]=kind
    result["requires_independent_review"]=True
    result["sent_to_hub"]=False
    result["verdict"]="observation_only"
    return result

def save_private_new(path,obj):
    destination=pathlib.Path(path)
    if destination.is_symlink() or destination.exists():
        raise ValueError("will not replace pre-existing or symlink output")
    if not destination.parent.is_dir():
        raise ValueError("output directory must exist")
    fd,temp=tempfile.mkstemp(prefix=".passive-",dir=destination.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            json.dump(obj,out,sort_keys=True,ensure_ascii=False,indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp,0o600)
        os.rename(temp,destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def main():
    parser=argparse.ArgumentParser(description="Authorized local log -> privacy-safe summary")
    parser.add_argument("--input",required=True)
    parser.add_argument("--source-kind",choices=ALLOWED_SOURCES,required=True)
    parser.add_argument("--authorized",action="store_true",
        help="explicitly affirm ownership or permission to process this log")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result=process(args.input,args.source_kind,args.authorized)
    save_private_new(args.output,result)
    print('{"status":"saved_locally","sent_to_hub":false,"privacy_summary":true}')

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit("passive import refused: "+type(exc).__name__)
