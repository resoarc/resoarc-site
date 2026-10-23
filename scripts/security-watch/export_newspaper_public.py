#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""Read only approved public SWWW records from the localhost-only PostgreSQL API.

Safe for the VPS; all response fields are allowlisted and no private assessments
are read. Output is JSON on stdout or nonzero status (never partial content).
"""
from __future__ import annotations
import json,sys,urllib.request,urllib.parse,datetime as dt

API="http://127.0.0.1:18763"
MAX_ITEMS=700
ALLOW={"id","source","sources","cves","title","summary","url","published_date","severity",
 "cvss","epss","known_exploited","technologies","resoarc_impact","resoarc_response","response_difficulty"}
FORBID={"internal_owner","affected_asset","investigation_notes","private_notes",
        "host","host_ip","verification_ref","remediation","difficulty_evidence"}

def fetch(path):
    req=urllib.request.Request(API+path,headers={"Accept":"application/json",
          "User-Agent":"ResoArc-SWWW-Newspaper/1.0"})
    with urllib.request.urlopen(req,timeout=12) as r:
        assert r.status==200
        body=r.read(420001)
        if len(body)>420000:raise ValueError("response_too_large")
        return json.loads(body)

def build():
    summary=fetch("/v1/summary")
    assert summary["schema_version"]=="1.1"
    assert summary["quality"]=="OK"
    assert summary["source_count"]>=10
    day=dt.date.fromisoformat(summary["report_date"])
    generated=dt.datetime.fromisoformat(summary["generated_at"])
    if generated.tzinfo is None or generated.date()!=day:
        raise ValueError("report_datetime_invalid")
    now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
    if day!=now.date():
        raise ValueError("no_approved_report_for_today")
    age=(now-generated.astimezone(now.tzinfo)).total_seconds()/60
    if age<0 or age>240:raise ValueError("report_is_not_fresh_enough")
    rows=[]
    total=None
    for page in range(1,9):
        query=urllib.parse.urlencode({"date":summary["report_date"],"limit":100,"page":page})
        response=fetch("/v1/advisories?"+query)
        if response["quality"]!="OK" or response["report_date"]!=summary["report_date"]:
            raise ValueError("report_changed_mid_export")
        size=int(response["filtered_total"])
        if size>MAX_ITEMS:raise ValueError("daily_list_is_too_large")
        if total is None:total=size
        if size!=total:raise ValueError("daily_list_changed_mid_export")
        for row in response["items"]:
            if not set(row).issubset(ALLOW):raise ValueError("unexpected_field_in_public_api")
            if FORBID & set(row):raise ValueError("private_field_in_public_api")
            if row["published_date"]!=summary["report_date"]:
                raise ValueError("other_date_in_daily_list")
            if row["resoarc_impact"] not in ("NOT_CONFIRMED","UNREVIEWED"):
                raise ValueError("unapproved_resoarc_disclosure")
            rows.append({k:row[k] for k in ALLOW if k in row})
        if not response["has_next"]:break
    if total is None or len(rows)!=total:raise ValueError("missing_daily_records")
    tag_response=fetch("/v1/technologies")
    if tag_response["quality"]!="OK" or tag_response["report_date"]!=summary["report_date"]:
        raise ValueError("tags_changed_mid_export")
    tags=[{"id":str(t["id"])[:55],"label":str(t["label"])[:65],
           "count":int(t["count"])} for t in tag_response["technologies"][:40]]
    meta={"date":summary["report_date"],"generated_at":summary["generated_at"],"quality":"OK",
          "source_count":summary["source_count"],"archive_total":summary["archive_total"],
          "daily_archive_total":summary["daily_archive_total"],
          "published_date_count":len(rows),"version":"newspaper-daily-1"}
    return {"metadata":meta,"items":rows,"technologies":tags}

def main():
    try:
        result=build()
        json.dump(result,sys.stdout,ensure_ascii=False,separators=(",",":"),sort_keys=True)
        sys.stdout.write("\n")
    except Exception as exc:
        print("SWWW_NEWSPAPER_EXPORT_REJECTED",type(exc).__name__,str(exc)[:150],file=sys.stderr)
        return 2
    return 0
if __name__=="__main__":sys.exit(main())
