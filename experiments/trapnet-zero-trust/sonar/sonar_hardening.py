#!/usr/bin/env python3
"""TrapNet privacy-preserving read-only telemetry and Sonar fingerprint diagnostics.

Python stdlib only. No login, outbound HTTP, traffic interception, firewall or command execution,
except allowlisted 'docker inspect' for coverage. No raw request, credential or client IP output.
"""
from __future__ import annotations
import argparse
import collections
import datetime
import http.client
import json
import pathlib
import re
import subprocess
import sys
import time

MAX_LINE=8192
MAX_RECORDS=40000
MIN_PUBLIC=5
CATEGORIES=("auth","admin","metadata","config","api","database","other")
CONTAINER_NAMES=("trapnet-cowrie-stage","trapnet-web-stage","trapnet-edge-stage")

def category_for(path):
    p=path.lower()[:256].split("?",1)[0]
    if any(x in p for x in ("/login","/auth","/signin","/wp-login")): return "auth"
    if any(x in p for x in ("/admin","/dashboard","/manager","/console")): return "admin"
    if any(x in p for x in ("/.env","/config","/.git","/backup","/secret")): return "config"
    if any(x in p for x in ("/db/","/sql","/database","/query")): return "database"
    if any(x in p for x in ("/meta","/health","/actuator","/version")): return "metadata"
    if p.startswith("/api/") or p.startswith("/graphql") or p.startswith("/mcp"): return "api"
    return "other"

def status_family(v):
    try:
        n=int(v)
        if 100<=n<=599:return str(n//100)+"xx"
    except (TypeError,ValueError): pass
    return "unknown"

def safe_records(stream):
    """Parse bounded JSON observation events or conventional HTTP common logs. Discard IPs/raw paths."""
    parsed=0
    for line in stream:
        if parsed>=MAX_RECORDS:break
        if len(line)>MAX_LINE:continue
        path=None;status=None
        try:
            obj=json.loads(line)
            if isinstance(obj,dict):
                path=obj.get("path") if isinstance(obj.get("path"),str) else None
                status=obj.get("status")
                if path is None and isinstance(obj.get("request"),str):
                    m=re.match(r"^(GET|HEAD|POST|PUT|DELETE|OPTIONS|PATCH)\s+(\S+)\s+HTTP/",obj["request"])
                    if m: path=m.group(2)
                if path is None and isinstance(obj.get("url_path"),str): path=obj["url_path"]
        except (ValueError,TypeError):
            # Only extract request line and status, not remote IP or quoted user agent.
            m=re.search(r'"(?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS)\s+([^\s"]{1,256})\s+HTTP/[0-9.]+"\s+([1-5][0-9][0-9])\s',line)
            if m:path=m.group(1);status=m.group(2)
        if path is None:continue
        parsed+=1
        yield category_for(path),status_family(status)

def bucket(n,minimum=MIN_PUBLIC):
    if n<minimum:return "<"+str(minimum)
    # Coarse lower/upper ranges; do not publish exact small cohorts.
    if n<10:return "5-9"
    if n<50:return "10-49"
    if n<100:return "50-99"
    if n<500:return "100-499"
    return "500+"

def aggregate(stream,min_public=MIN_PUBLIC):
    events=list(safe_records(stream))
    paths=collections.Counter(x for x,_ in events)
    statuses=collections.Counter(y for _,y in events)
    return {
        "schema":"trapnet.public-aggregate.v1",
        "privacy":{"raw_ip_exported":False,"node_ids_exported":False,
                   "raw_ua_exported":False,"raw_path_exported":False,
                   "raw_headers_exported":False,"small_counts_suppressed":True},
        "observations_band":bucket(len(events),min_public),
        "path_category_bands":{k:bucket(paths[k],min_public) for k in CATEGORIES if paths[k]>=min_public},
        "status_family_bands":{k:bucket(v,min_public) for k,v in sorted(statuses.items()) if v>=min_public},
        "small_cohorts_omitted":True,
        "classification":"unverified_observation_not_attack",
    }

def fingerprint_local(host="127.0.0.1",port=8086):
    """Only the LOCAL loopback endpoint, never an external host or port scan."""
    if host!="127.0.0.1" or not (1<=int(port)<=65535):raise ValueError("localhost-only fingerprint audit")
    observations=[];findings=set()
    for path in ("/","/openapi.json","/api/v1/keys","/unlikely-no-such-path-v3"):
        conn=http.client.HTTPConnection("127.0.0.1",int(port),timeout=3)
        try:
            conn.request("GET",path,headers={"User-Agent":"TrapNet-Local-Fingerprint-Audit/1.0"})
            response=conn.getresponse()
            data=response.read(8192)
            hdr={k.lower():v for k,v in response.getheaders()}
            text=data.decode("utf-8","replace").lower()
            if any(k in text for k in ("resoarc","trapnet","decoy_not_","synthetic_")):findings.add("explicit_decoy_marker_in_response")
            if "x-powered-by" in hdr:findings.add("stack_header_present")
            if "server" in hdr:findings.add("server_banner_present")
            observations.append({"route_class":category_for(path),"http_status":response.status,"response_size_band":bucket(len(data),5),
                                 "server_header_present":"server" in hdr})
        finally:conn.close()
    return {"schema":"trapnet.sonar-fingerprint-local.v1","scope":"loopback-only",
            "finding_codes":sorted(findings),"tested_routes":observations,
            "limitation":"Not proof that an external observer cannot fingerprint this deployment."}

def coverage():
    services={}
    for name in CONTAINER_NAMES:
        try:
            p=subprocess.run(["docker","inspect","--format","{{.State.Running}}",name],
                             capture_output=True,text=True,timeout=3,check=False)
            services[name.split("-")[1] if name.endswith("-stage") else name]=(
                "running" if p.returncode==0 and p.stdout.strip()=="true" else "unavailable")
        except (OSError,subprocess.TimeoutExpired):services[name.split("-")[1]]="unavailable"
    return {"schema":"trapnet.coverage-health.v1","runtime_services":services,
            "geographic_coverage_proven":False,"unique_independent_nodes_known":False,
            "classification":"service_health_only_not_detection_coverage"}

def evasion(samples):
    """Offline comparison of approved, pre-aggregated cohorts. Never infer intent."""
    if not isinstance(samples,list) or len(samples)>500:raise ValueError("expected bounded aggregate list")
    totals={"known":{"events":0,"hours":0.0,"windows":0},
            "heldout":{"events":0,"hours":0.0,"windows":0}}
    for row in samples:
        if not isinstance(row,dict):raise ValueError("sample must be object")
        cohort=row.get("cohort")
        if cohort not in totals:raise ValueError("unknown cohort")
        events=row.get("events");hours=row.get("exposure_hours")
        if type(events)!=int or events<0 or events>10000000 or type(hours) not in (int,float) or not 0<float(hours)<=744:
            raise ValueError("invalid sample")
        totals[cohort]["events"]+=events
        totals[cohort]["hours"]+=float(hours)
        totals[cohort]["windows"]+=1
    a,b=totals["known"],totals["heldout"]
    adequate=all(x["events"]>=20 and x["hours"]>=24 and x["windows"]>=3 for x in (a,b))
    result={"schema":"trapnet.evasion-indicator.v1","verdict":"insufficient_evidence",
            "causal_attribution":False,"operator_independence_verified":False,
            "sample_threshold_met":adequate}
    if adequate:
        ra=a["events"]/a["hours"];rb=b["events"]/b["hours"]
        result["relative_known_to_heldout_rate_band"]=(
            "<0.5" if ra/rb<.5 else "0.5-0.8" if ra/rb<.8 else "0.8-1.25" if ra/rb<1.25 else ">1.25")
        result["verdict"]="candidate_difference_review_only"
    result["confounders"]=["ASN","address_age","time_window","service_exposure","scanner_population"]
    return result

def input_lines(path):
    p=pathlib.Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>8*1024*1024:raise ValueError("file missing, symlink or oversized")
    with p.open("r",encoding="utf-8",errors="replace") as stream:
        yield from stream

def main(argv=None):
    ap=argparse.ArgumentParser(description="TrapNet safe diagnostics; no raw IP/user data in output")
    sp=ap.add_subparsers(dest="action",required=True)
    p=sp.add_parser("passive");p.add_argument("--input",required=True);p.add_argument("--output")
    q=sp.add_parser("fingerprint-local");q.add_argument("--port",type=int,default=8086)
    sp.add_parser("coverage")
    e=sp.add_parser("evasion");e.add_argument("--input",required=True)
    opts=ap.parse_args(argv)
    if opts.action=="passive":result=aggregate(input_lines(opts.input))
    elif opts.action=="fingerprint-local":result=fingerprint_local(port=opts.port)
    elif opts.action=="coverage":result=coverage()
    else:
        samples=json.loads("".join(input_lines(opts.input)))
        result=evasion(samples)
    raw=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    if opts.action=="passive" and opts.output:
        target=pathlib.Path(opts.output)
        if target.is_symlink():raise ValueError("refusing symlink output")
        with target.open("x",encoding="utf-8") as f:f.write(raw)
        target.chmod(0o600)
    else:print(raw,end="")
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as exc:
        print("diagnostic_failure:"+type(exc).__name__,file=sys.stderr)
        sys.exit(2)
