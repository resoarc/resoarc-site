#!/usr/bin/env python3
"""SWWW public API feed contracts, XML compliance and privacy regression tests."""
from pathlib import Path
import sys,json,xml.etree.ElementTree as ET,hashlib
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from swww_public import public_advisory,public_catalog,xml_catalog,xml_feed
p=root/"site/api/v1/swww"
report=json.loads((root/"site/security/weather/today.json").read_text(encoding="utf-8"))
cat=json.loads((p/"catalog.json").read_text(encoding="utf-8"))
assert cat["schema_version"]=="1.0"
assert cat["report_date"]==report["date"]
assert cat["quality"] in ("OK","PARTIAL")
assert cat["available_records"]==250==len(cat["advisories"])
assert cat["source_count"]==13
assert len({r["id"] for r in cat["advisories"]})==250
assert len(report["items"])==len(cat["advisories"])
assert all(isinstance(r["technologies"],list) for r in cat["advisories"])
print("PASS catalog accurate, count=250, sources=13")
allow={"id","cves","title","summary","source","sources","url","published_date","severity",
       "epss","known_exploited","technologies","resoarc_impact","resoarc_response","response_difficulty"}
assert all(set(row)==allow for row in cat["advisories"])
assert all(len(r["summary"])<=400 and len(r["title"])<=300 for r in cat["advisories"])
for bad in ("internal_owner","affected_asset","investigation_notes","remediation",
            "verification_ref","difficulty_evidence","private_register","weather-assessments",
            "security-weather-operations"):
 assert bad not in json.dumps(cat,ensure_ascii=False)
print("PASS strict public-field allowlist, no private details, descriptions clipped")
t=json.loads((p/"tags.json").read_text(encoding="utf-8"))
assert t["report_date"]==cat["report_date"]
assert 15<=len(t["technologies"])<=50
ids={x["id"] for x in t["technologies"]}
assert {"java","oracle","php"}.issubset(ids)
assert all(tag["id"] in ids for r in cat["advisories"] for tag in r["technologies"])
print("PASS technology tags, including Java/Oracle/PHP")
rss=ET.parse(p/"rss.xml").getroot()
assert rss.tag=="rss" and rss.attrib["version"]=="2.0"
rss_items=rss.findall("./channel/item")
assert len(rss_items)==100
assert rss.findtext("./channel/title")=="ResoArc SWWW 脆弱性天気予報"
atom=ET.parse(p/"atom.xml").getroot()
ns={"a":"http://www.w3.org/2005/Atom"}
atom_entries=atom.findall("./a:entry",ns)
assert len(atom_entries)==100
assert atom.findtext("./a:title",namespaces=ns)=="ResoArc SWWW 脆弱性天気予報"
assert all(ent.find("./a:updated",ns) is not None for ent in atom_entries)
xml=ET.parse(p/"advisories.xml").getroot()
urn={"s":"https://resoarc.com/ns/swww/1"}
assert xml.tag=="{https://resoarc.com/ns/swww/1}catalog"
assert len(xml.findall("./s:advisories/s:advisory",urn))==250
assert xml.findtext("./s:report_date",namespaces=urn)==cat["report_date"]
feed=json.loads((p/"feed.json").read_text(encoding="utf-8"))
assert feed["version"]=="https://jsonfeed.org/version/1.1" and len(feed["items"])==100
print("PASS standards XML/RSS/Atom/JSON feeds (100/100/250/100 records)")
api=json.loads((p/"openapi.json").read_text(encoding="utf-8"))
assert api["openapi"]=="3.1.0"
for endpoint in ("/api/v1/swww/advisories","/api/v1/swww/summary",
                 "/api/v1/swww/technologies","/api/v1/swww/advisories.xml",
                 "/api/v1/swww/rss.xml","/api/v1/swww/atom.xml","/api/v1/swww/feed.json"):
 assert endpoint in api["paths"],endpoint
landing=(p/"index.html").read_text(encoding="utf-8")
assert all(endpoint in landing for endpoint in ("advisories.xml","rss.xml","atom.xml","feed.json","openapi.json"))
assert "脆弱性" in landing and "蜈" not in landing
assert "class=\"site-header\"" in landing
print("PASS OpenAPI contract and accessible Japanese documentation")
assert "internal_owner" not in landing
assert all("internal_owner" not in (p/file).read_text(encoding="utf-8")
  for file in ("feed.json","catalog.json","index.html","openapi.json","tags.json"))
assert all("internal_owner" not in (p/file).read_text(encoding="utf-8")
  for file in ("rss.xml","atom.xml","advisories.xml"))
malicious={"id":"X","url":"javascript:alert(1)","title":"<script>unsafe</script>",
 "summary":"<script>x</script>","technology_tags":[],"source":"test","source_refs":["test"],
 "date":"2026-10-22"}
out=public_advisory(malicious)
assert out["url"]=="#" and "<script>" in out["title"]
report2={"date":"2026-10-22","generated_at":cat["generated_at"],"items":[malicious],
         "observed":{"total":1},"source_count":13}
malicious_xml=xml_catalog(report2).decode("utf-8")
assert "<script>" not in malicious_xml and "&lt;script&gt;" in malicious_xml
print("PASS unsafe links blocked and XML escapes hostile source text")
assert "https://resoarc.com/api/v1/swww/" in landing
print("SWWW_PUBLIC_API_FEED_TESTS 7/7 PASS")
