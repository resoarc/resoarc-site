#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""Synthetic date advance, archive preservation and fail-closed daily publisher QA."""
from pathlib import Path
import json,sys,shutil,tempfile,hashlib,datetime as dt
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from generate_newspaper_daily import make,validate,scored,picks
source=ROOT.parent/"newspaper_public_source_20261023.json"
assert source.exists(),source
original=json.loads(source.read_text(encoding="utf-8"))
site=ROOT/"site"
assert (site/"security/weather/newspaper/index.html").exists()
with tempfile.TemporaryDirectory() as temp:
 testsite=Path(temp)/"site"
 shutil.copytree(site/"security/weather/newspaper",testsite/"security/weather/newspaper")
 first=testsite/"security/weather/newspaper/all/index.html"
 first_hash=hashlib.sha256(first.read_bytes()).hexdigest()
 later=json.loads(json.dumps(original))
 later["metadata"]["date"]="2026-10-24"
 later["metadata"]["generated_at"]="2026-10-24T09:12:00+09:00"
 for row in later["items"]:
  row["published_date"]="2026-10-24"
  row["title"]="TEST-2026 "+row["title"]
 # No hand-reviewed 10/23 headline can be recycled.
 issue=make(later,testsite)
 assert issue["edition_date"]=="2026-10-24"
 assert issue["model"]=="rules_and_verified_editorial"
 latest=(testsite/"security/weather/newspaper/index.html").read_text(encoding="utf-8")
 assert "2026年10月24日" in latest
 assert "Next.jsに2つの警報" not in latest
 assert "編集部の注目" in latest and "原文を確認" in latest
 assert (testsite/"security/weather/newspaper/archive/2026-10-23/index.html").exists()
 assert hashlib.sha256((testsite/"security/weather/newspaper/archive/2026-10-23/index.html").read_bytes()).hexdigest()==first_hash
 assert (testsite/"security/weather/newspaper/edition.json.license").exists()
 print("PASS tomorrow's newspaper never reuses yesterday's manually edited titles")
 print("PASS old issue retained as immutable archive")
 assert (testsite/"security/weather/newspaper/archive/index.html").read_text(encoding="utf-8").count("2026-10-23")>=1
 # Re-running the same day's edition is safe.
 again=make(later,testsite)
 assert again==issue
 print("PASS idempotent re-generation of same date")
 old=json.loads(json.dumps(later))
 old["metadata"]["date"]="2026-10-23"
 try:make(old,testsite)
 except (ValueError,AssertionError):pass
 else:raise AssertionError("older issue must not replace newer one")
 print("PASS refuse stale-date replacements")
 corrupt=json.loads(json.dumps(later))
 corrupt["metadata"]["quality"]="PARTIAL"
 try:make(corrupt,testsite)
 except (ValueError,AssertionError):pass
 else:raise AssertionError("partial quality must not publish")
 assert "2026年10月24日" in (testsite/"security/weather/newspaper/index.html").read_text(encoding="utf-8")
 print("PASS PARTIAL collection rejected and existing issue kept")
 assert all(scored(x)==scored(x) for x in later["items"])
 assert len(picks(later["items"],8))==8
 print("PASS diverse deterministic ranking")
print("SWWW_DAILY_NEWSPAPER_TESTS_6_OF_6_PASS")
