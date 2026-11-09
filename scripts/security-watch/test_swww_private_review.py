#!/usr/bin/env python3
"""Regression tests: project review privacy, evidence, and honest counts."""
import datetime as dt
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import weather_report as w
from swww_assessments import get_review,public_projection,private_register,private_html

def sample_item(id,sev):
 return {"id":id,"source":"GitHub Advisory","title":"External advisory "+id,
         "summary":"Public advisory text","published":"2026-10-22T04:00:00Z",
         "url":"https://github.com/advisories/"+id,"severity":sev,"scope":"industry"}

queue={"status":"FETCHED_UNREVIEWED","checked_at":"2026-10-22T05:00:00Z",
       "sources":{k:"OK" for k in w.SOURCES},"errors":[],
       "items":[sample_item("GHSA-1111-2222-3333","CRITICAL"),sample_item("GHSA-4444-5555-6666","HIGH")]}
triage={"counts":{"P1":20,"P2":69}}
now=dt.datetime(2026,10,22,14,10,tzinfo=w.JST)
key="GHSA-1111-2222-3333"
sensitive="INTERNAL-PRODUCTION-HOST-NEVER-PUBLISH"
assessments={key:{"resoarc_impact":"AFFECTED","response_status":"REMEDIATED",
                 "difficulty":"hard","difficulty_evidence":"8h maintenance",
                 "affected_asset":sensitive,"internal_owner":"secret-person",
                 "investigation_notes":"PRIVATE-"+sensitive,
                 "remediation":"patch by internal SSH",
                 "reviewed_by":"reviewer","reviewed_at":"2026-10-22T12:00:00+09:00",
                 "evidence_ref":"private-evidence","verification_ref":"verified-test",
                 "public_approved":False}}
report=w.build_report(queue,triage,assessments,now=now)
assert report["today"]["new"]==2
assert report["today"]["difficulty"]=={"easy":0,"moderate":0,"hard":0,"unknown":2}
assert report["resoarc_review"]["impact"]=={"affected":0,"not_affected":0,"unreviewed":2}
assert report["resoarc_review"]["response"]["UNREVIEWED"]==2
assert all(x["response_status"]=="UNREVIEWED" and x["resoarc_impact"]=="NOT_CONFIRMED" for x in report["items"])
assert sensitive not in json.dumps(report,ensure_ascii=False)
assert "secret-person" not in json.dumps(report,ensure_ascii=False)
print("PASS private assessment denied publication even when internal fields contain confirmed statuses")
private=private_register(report,assessments,triage,[{"date":"2026-10-22","title":"Platform patch","status":"VERIFIED","notes":sensitive}])
private_json=json.dumps(private,ensure_ascii=False)
assert sensitive in private_json and private["entries"][0]["response"]=="REMEDIATED"
assert private["operations"][0]["title"]=="Platform patch"
assert sensitive not in json.dumps(report,ensure_ascii=False)
print("PASS separate private register retains details and operations")
assessments[key]["public_approved"]=True
report=w.build_report(queue,triage,assessments,now=now)
assert report["resoarc_review"]["impact"]["affected"]==1
assert report["resoarc_review"]["response"]["REMEDIATED"]==1
assert report["today"]["difficulty"]["hard"]==1
assert "INTERNAL-PRODUCTION-HOST" not in json.dumps(report,ensure_ascii=False)
assert "secret-person" not in json.dumps(report,ensure_ascii=False)
print("PASS human-approved evidenced counts only, never private asset or owner")
assessments[key].pop("verification_ref")
report=w.build_report(queue,triage,assessments,now=now)
assert report["resoarc_review"]["response"]["REMEDIATED"]==0
assert report["resoarc_review"]["response"]["INVESTIGATING"]==1
print("PASS remediation requires verification evidence")
assessments[key].pop("difficulty_evidence")
report=w.build_report(queue,triage,assessments,now=now)
assert report["today"]["difficulty"]["hard"]==0
assert report["today"]["difficulty"]["unknown"]==2
print("PASS difficulty unknown until independent supporting evidence")
assessments[key].pop("evidence_ref")
report=w.build_report(queue,triage,assessments,now=now)
assert report["resoarc_review"]["impact"]["unreviewed"]==2
print("PASS disclosure rejected without evidence reference")
assessments[key]["investigation_notes"]="<script>alert('private')</script>"
text=private_html(private_register(report,assessments,triage,[]))
assert "<script>alert" not in text and "&lt;script&gt;" in text
print("PASS private report escapes potentially hostile reviewed content")
template=Path(__file__).resolve().with_name("weather_template.html").read_text(encoding="utf-8")
page=w.render_page(report,template)
assert "id=\"resoarc-status-title\"" in page and "id=\"ra-remediated\"" in page
assert "id=\"advisory-rows\"" in page
assert sensitive not in page
print("PASS generated report has public assessment widgets with no private data")
print("SWWW_RESOARC_ASSESSMENT_TESTS 7/7 PASS")
