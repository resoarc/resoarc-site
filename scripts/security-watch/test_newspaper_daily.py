#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""SWWW daily edition regression checks, independent of today's deployed date."""
from pathlib import Path
import datetime as dt, hashlib, json, shutil, sys, tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from generate_newspaper_daily import make, validate, scored, picks, data_hash
import export_newspaper_public as exporter

source=ROOT.parent/"newspaper_public_source_20261023.json"
assert source.exists(),source
original=json.loads(source.read_text(encoding="utf-8"))
site=ROOT/"site"
out="security/weather/newspaper"
assert (site/out/"edition.json").exists()

with tempfile.TemporaryDirectory() as temp:
    testsite=Path(temp)/"site"
    shutil.copytree(site/out,testsite/out)
    edition=json.loads((testsite/out/"edition.json").read_text(encoding="utf-8"))
    original_date=dt.date.fromisoformat(edition["edition_date"])
    issue_date=original_date+dt.timedelta(days=1)
    newdate=issue_date.isoformat()
    previous_archive=testsite/out/"all/index.html"
    previous_hash=hashlib.sha256(previous_archive.read_bytes()).hexdigest()
    later=json.loads(json.dumps(original))
    later["metadata"].update(date=newdate,generated_at=newdate+"T09:12:00+09:00",quality="OK",
                             source_count=13,published_date_count=len(later["items"]),
                             same_day_count=len(later["items"]),carryover_count=0,carryover_total=0)
    for row in later["items"]:
        row["published_date"]=newdate
        row["title"]="TEST-2026 "+row["title"]
    issue=make(later,testsite)
    assert issue["edition_date"]==newdate
    assert issue["render_version"]=="newspaper-daily-2"
    assert issue["content_sha256"]==data_hash(later)
    latest=(testsite/out/"index.html").read_text(encoding="utf-8")
    assert "編集部の注目" in latest and "原文を確認" in latest
    archive=testsite/out/"archive"/edition["edition_date"]/"index.html"
    assert archive.exists()
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==previous_hash
    assert (testsite/out/"edition.json.license").exists()
    print("PASS new date + previous-issue archive remains unchanged")

    same=make(later,testsite)
    assert same==issue
    later["items"][0]["title"]="UPDATED "+later["items"][0]["title"]
    changed=make(later,testsite)
    assert changed["content_sha256"]!=issue["content_sha256"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==previous_hash
    print("PASS same-day content changes and archive is preserved")

    carry=json.loads(json.dumps(later))
    prior_date=original_date.isoformat()
    for row in carry["items"]:
        row["published_date"]=prior_date
    carry["metadata"].update(same_day_count=0,carryover_count=len(carry["items"]),carryover_total=741)
    carry_issue=make(carry,testsite)
    carry_html=(testsite/out/"index.html").read_text(encoding="utf-8")
    assert carry_issue["same_day_count"]==0
    assert carry_issue["carryover_count"]==len(carry["items"])
    assert "前日付の注目情報" in carry_html
    assert "本日付の新着掲載は0件" in carry_html
    print("PASS previous-day carryover explicitly labelled, not misrepresented as fresh")

    bad=json.loads(json.dumps(carry))
    bad["metadata"]["quality"]="PARTIAL"
    try:make(bad,testsite)
    except (ValueError,AssertionError):pass
    else:raise AssertionError("PARTIAL must not publish")
    assert json.loads((testsite/out/"edition.json").read_text(encoding="utf-8"))==carry_issue
    print("PASS partial quality rejected without overwriting")

    outdated=json.loads(json.dumps(later))
    outdated["metadata"]["date"]=prior_date
    try:make(outdated,testsite)
    except (ValueError,AssertionError):pass
    else:raise AssertionError("stale edition must not publish")
    assert len(picks(later["items"],8))==8
    assert all(scored(x)==scored(x) for x in later["items"])
    print("PASS older-date rejection and deterministic ranking")

# Isolated exporter fixture: all rows are public API allowlisted values.
now=dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))
day=now.date()
previous=(day-dt.timedelta(days=1)).isoformat()
sample=dict(original["items"][0])
sample["published_date"]=previous
sample["resoarc_impact"]="NOT_CONFIRMED"
sample["resoarc_response"]="UNREVIEWED"
sample={k:v for k,v in sample.items() if k in exporter.ALLOW}
summary={"schema_version":"1.1","quality":"OK","source_count":13,
         "report_date":day.isoformat(),"generated_at":now.isoformat(),
         "archive_total":250,"daily_archive_total":250}
def fake_fetch(path):
    if path=="/v1/summary":return summary
    if path.startswith("/v1/technologies"):return {"quality":"OK","report_date":day.isoformat(),"technologies":[]}
    if "date="+day.isoformat() in path:
        return {"quality":"OK","report_date":day.isoformat(),"filtered_total":0,"items":[],"has_next":False}
    if "date="+previous in path:
        return {"quality":"OK","report_date":day.isoformat(),"filtered_total":1,"items":[sample],"has_next":False}
    raise AssertionError("unexpected public API call "+path)
exporter.fetch=fake_fetch
result=exporter.build()
assert result["metadata"]["date"]==day.isoformat()
assert result["metadata"]["same_day_count"]==0
assert result["metadata"]["carryover_count"]==1
assert result["metadata"]["carryover_total"]==1
assert result["items"][0]["published_date"]==previous
validate(result)
print("PASS read-only public API previous-day fallback and provenance validation")
print("SWWW_DAILY_NEWSPAPER_TESTS_6_OF_6_PASS")
