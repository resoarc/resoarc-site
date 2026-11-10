#!/usr/bin/env python3
"""Public-only SWWW rendering + open machine-readable feeds. No private registers."""
from __future__ import annotations
import datetime as dt
import html
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import format_datetime
from pathlib import Path
from swww_tags import classify, TAXONOMY

BASE="https://resoarc.com"
VERSION="1.0"
MAX_ROW=500
GROUPS={"vendor","runtime","os","devops","infra","database","cms","browser","cloud","platform","framework"}

def enrich(report):
    counts={}
    for row in report.get("items",[]):
        tags=classify(row)
        row["technology_tags"]=tags
        for t in tags:counts[t["id"]]=counts.get(t["id"],0)+1
    report["technology_summary"]=[
        {"id":tid,"label":TAXONOMY[tid]["label"],"group":TAXONOMY[tid]["group"],"count":n}
        for tid,n in sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))
    ]
    report["technology_semantics"]="タグは公開情報に登場する製品・技術の分類で、ResoArcでの使用・影響の確認ではありません。"
    return report

def safe_url(u):
    try:
        p=urllib.parse.urlsplit(str(u or ""))
        if p.scheme=="https" and p.hostname and not p.username and not p.password:
            return u
    except ValueError:
        pass
    return "#"

def esc(v):
    return html.escape(str(v or ""),quote=True)

def tag_html(tags):
    if not tags:return '<span class="tech-unknown">技術未分類</span>'
    return "".join('<span class="swww-tech-tag tech-'+esc(t["group"])+
                   '" title="公開情報の記載に基づく分類">'+esc(t["label"])+'</span>'
                   for t in tags)

def static_rows(report,only_today=True):
    day=report.get("date")
    rows=[x for x in report.get("items",[])
          if not only_today or x.get("date")==day or x.get("kev_date")==day]
    rendered=[]
    for x in rows[:MAX_ROW]:
        link=safe_url(x.get("url"))
        sev=str(x.get("severity","UNKNOWN")).upper()
        if sev not in ("CRITICAL","HIGH","MEDIUM","LOW"):sev="UNKNOWN"
        ep=x.get("epss")
        epss="未収集" if not isinstance(ep,(int,float)) else f"{max(0,min(100,ep*100)):.1f}%"
        parts=[
            '<a href="'+esc(link)+'" target="_blank" rel="noopener noreferrer">'+
              esc(x.get("id",""))+" · "+esc(x.get("title",""))+"</a><small>"+
              esc(x.get("date",""))+" / "+esc("・".join(x.get("source_refs") or [x.get("source","")]))+"</small>",
            '<span class="tag '+sev.lower()+'">'+esc(sev)+'</span>',
            tag_html(x.get("technology_tags",[])),
            esc(epss),
            "既知の悪用" if x.get("exploited_in_wild") else "確認情報なし",
            esc(x.get("difficulty_label","要調査")),
            esc(x.get("impact_level","未判定")),
            "影響確認" if x.get("resoarc_impact")=="AFFECTED" else
              "対象外と審査済" if x.get("resoarc_impact")=="NOT_AFFECTED" else "未判定",
            esc(x.get("response_status_label","未審査"))
        ]
        rendered.append('<tr data-source-render="server">'+''.join('<td>'+part+'</td>' for part in parts)+'</tr>')
    if not rendered:
        return '<tr data-source-render="server"><td colspan="9">該当する新着情報はありません。取得状態を確認してください。</td></tr>'
    return '\n'.join(rendered)

def replace_static_text(page, element_id, new_value):
    pattern=r'(<([a-zA-Z][\w-]*)\b[^>]*\bid="'+re.escape(element_id)+r'"[^>]*>)([\s\S]*?)(</\2>)'
    return re.sub(pattern,lambda m:m.group(1)+esc(new_value)+m.group(4),page,count=1)

def render_public_page(report,template,safe_json):
    # A fully readable HTML document with JS disabled or blocked by an extension.
    # JS enhances filtering but does not own the sole copy of the report.
    if "__SWWW_STATIC_ROWS__" not in template:
        raise ValueError("Template missing static no-JavaScript rows")
    page=template.replace("__SWWW_STATIC_ROWS__",static_rows(report))
    new=int(report["today"]["new"])
    project=report.get("resoarc_review",{})
    impacts=project.get("impact",{})
    status=project.get("response",{})
    values={
        "new-count":new,
        "critical-count":report["today"].get("critical",0),
        "kev-count":report["today"].get("kev",0),
        "difficulty-count":"要調査 "+str(report["today"].get("difficulty",{}).get("unknown",new))+"件",
        "ra-affected":str(impacts.get("affected",0))+"件",
        "ra-not-affected":str(impacts.get("not_affected",0))+"件",
        "ra-unreviewed":str(impacts.get("unreviewed",new))+"件",
        "ra-remediated":str(status.get("REMEDIATED",0))+"件",
        "ra-unreviewed-response":"未審査 "+str(status.get("UNREVIEWED",new))+"件",
        "ra-investigating-response":"調査中 "+str(status.get("INVESTIGATING",0))+"件",
        "ra-active-response":"対策予定・実施中 "+str(status.get("PLANNED",0)+status.get("MITIGATING",0))+"件",
        "weather-label":report["today"]["weather"]["label"],
        "weather-icon":report["today"]["weather"]["icon"],
        "weather-sub":report["today"]["weather"]["subtitle"],
        "date-head":report.get("date",""),
        "checked-head":"観測データ："+report.get("generated_at","")[:19]+" JST",
        "quality":"取得済み / 正常" if report.get("quality")=="OK" else "一部欠測 / 参考値",
        "listed-count":"表示 "+str(min(new,MAX_ROW))+"件 / 統合 "+str(report["observed"]["total"])+"件"
    }
    for key,value in values.items():page=replace_static_text(page,key,value)
    return page.replace("__SWWW_DATA__",safe_json)

def public_advisory(row):
    tags=[{"id":t["id"],"label":t["label"],"group":t["group"]} for t in row.get("technology_tags",[])]
    return {
        "id":str(row.get("id",""))[:90],
        "cves":list(row.get("cves") or [])[:15],
        "title":str(row.get("title",""))[:300],
        "summary":str(row.get("summary",""))[:400],
        "source":str(row.get("source",""))[:64],
        "sources":list(row.get("source_refs") or [row.get("source","")])[:20],
        "url":safe_url(row.get("url")),
        "published_date":str(row.get("date",""))[:10],
        "severity":str(row.get("severity","UNKNOWN"))[:18].upper(),
        "epss":row.get("epss") if isinstance(row.get("epss"),(int,float)) else None,
        "known_exploited":bool(row.get("exploited_in_wild")),
        "technologies":tags,
        "resoarc_impact":str(row.get("resoarc_impact","NOT_CONFIRMED")),
        "resoarc_response":str(row.get("response_status","UNREVIEWED")),
        "response_difficulty":str(row.get("difficulty","unknown"))
    }

def public_catalog(report):
    # Explicit allowlist is also the privacy boundary between JSON files and API.
    rows=[public_advisory(x) for x in report.get("items",[])]
    return {
       "schema_version":"1.0",
       "license":"Original advisory content and licensing remain with their publishers; no blanket redistribution license is claimed.",
       "service":"ResoArc SWWW",
       "report_date":report.get("date"),
       "generated_at":report.get("generated_at"),
       "quality":report.get("quality"),
       "source_count":report.get("source_count"),
       "observed_total":int(report.get("observed",{}).get("total",0)),
       "available_records":len(rows),
       "collection_limit_notice":"Only the verified public snapshot's current item set is provided. This endpoint is not an exhaustive CVE archive.",
       "advisories":rows
    }

def rfc2822(date):
    try:
        d=dt.datetime.fromisoformat(str(date).replace("Z","+00:00"))
        if d.tzinfo is None:d=d.replace(tzinfo=dt.timezone.utc)
        return format_datetime(d.astimezone(dt.timezone.utc),usegmt=True)
    except Exception:
        return format_datetime(dt.datetime.now(dt.timezone.utc),usegmt=True)

def xml_feed(report,atom=False,limit=100):
    advisories=public_catalog(report)["advisories"]
    advisories=[x for x in advisories if x["published_date"]==report["date"]][:limit]
    if atom:
        ns="http://www.w3.org/2005/Atom"
        ET.register_namespace("",ns)
        elt=lambda name: "{"+ns+"}"+name
        root=ET.Element(elt("feed"))
        ET.SubElement(root,elt("title")).text="ResoArc SWWW 脆弱性天気予報"
        ET.SubElement(root,elt("id")).text=BASE+"/security/weather/"
        ET.SubElement(root,elt("updated")).text=report["generated_at"]
        ET.SubElement(root,elt("link"),{"rel":"self","href":BASE+"/api/v1/swww/atom.xml"})
        ET.SubElement(root,elt("link"),{"rel":"alternate","href":BASE+"/security/weather/"})
        for item in advisories:
            ent=ET.SubElement(root,elt("entry"))
            ET.SubElement(ent,elt("id")).text=BASE+"/security/weather/#"+item["id"]
            ET.SubElement(ent,elt("title")).text=item["title"][:240]
            ET.SubElement(ent,elt("updated")).text=item["published_date"]+"T00:00:00+09:00"
            ET.SubElement(ent,elt("link"),{"href":safe_url(item["url"])})
            ET.SubElement(ent,elt("summary")).text=item["summary"][:400]
            for tag in item["technologies"]:
                ET.SubElement(ent,elt("category"),{"term":tag["id"],"label":tag["label"]})
    else:
        root=ET.Element("rss",{"version":"2.0"})
        ch=ET.SubElement(root,"channel")
        ET.SubElement(ch,"title").text="ResoArc SWWW 脆弱性天気予報"
        ET.SubElement(ch,"link").text=BASE+"/security/weather/"
        ET.SubElement(ch,"description").text="一般公開脆弱性情報。ResoArcへの影響は根拠ある審査を経た情報のみ。"
        ET.SubElement(ch,"language").text="ja"
        ET.SubElement(ch,"lastBuildDate").text=rfc2822(report["generated_at"])
        for item in advisories:
            ent=ET.SubElement(ch,"item")
            ET.SubElement(ent,"title").text=item["id"]+" · "+item["title"][:240]
            ET.SubElement(ent,"link").text=safe_url(item["url"])
            ET.SubElement(ent,"guid",{"isPermaLink":"false"}).text=item["id"]
            ET.SubElement(ent,"pubDate").text=rfc2822(item["published_date"]+"T00:00:00+09:00")
            ET.SubElement(ent,"description").text=item["summary"][:400]
            for tag in item["technologies"]:
                ET.SubElement(ent,"category").text=tag["label"]
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)

def xml_catalog(report):
    """Machine-readable public-only XML, separate from RSS/Atom."""
    cat=public_catalog(report)
    ns="https://resoarc.com/ns/swww/1"
    ET.register_namespace("swww",ns)
    element=lambda name: "{"+ns+"}"+name
    root=ET.Element(element("catalog"),{"version":"1.0"})
    for key in ("report_date","generated_at","quality","source_count","observed_total",
                "available_records","collection_limit_notice","license"):
        ET.SubElement(root,element(key)).text=str(cat[key])
    items=ET.SubElement(root,element("advisories"))
    for row in cat["advisories"]:
        item=ET.SubElement(items,element("advisory"),{"id":row["id"]})
        for key in ("title","summary","source","url","published_date","severity",
                    "known_exploited","resoarc_impact","resoarc_response","response_difficulty"):
            ET.SubElement(item,element(key)).text=str(row[key]).lower() if isinstance(row[key],bool) else str(row[key])
        if row["epss"] is not None:
            ET.SubElement(item,element("epss")).text=str(row["epss"])
        sources=ET.SubElement(item,element("sources"))
        for source in row["sources"]:
            ET.SubElement(sources,element("source")).text=str(source)
        cves=ET.SubElement(item,element("cves"))
        for cve in row["cves"]:
            ET.SubElement(cves,element("cve")).text=str(cve)
        tags=ET.SubElement(item,element("technologies"))
        for t in row["technologies"]:
            ET.SubElement(tags,element("technology"),{"id":t["id"],"group":t["group"]}).text=t["label"]
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)

def export_feeds(report,site_root):
    root=Path(site_root)/"api/v1/swww"
    root.mkdir(parents=True,exist_ok=True)
    cat=public_catalog(report)
    (root/"catalog.json").write_text(json.dumps(cat,ensure_ascii=False,sort_keys=True,separators=(',',':'))+"\n",encoding="utf-8")
    (root/"tags.json").write_text(json.dumps({"report_date":report["date"],"technologies":report["technology_summary"],
                "caveat":report["technology_semantics"]},ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (root/"rss.xml").write_bytes(xml_feed(report,False))
    (root/"advisories.xml").write_bytes(xml_catalog(report))
    (root/"atom.xml").write_bytes(xml_feed(report,True))
    (root/"feed.json").write_text(json.dumps({
      "version":"https://jsonfeed.org/version/1.1","title":"ResoArc SWWW",
      "home_page_url":BASE+"/security/weather/",
      "feed_url":BASE+"/api/v1/swww/feed.json",
      "description":"公開の脆弱性情報と技術タグ。ResoArc製品への影響を示すものではありません。",
      "items":[{
         "id":x["id"],"url":x["url"],"title":x["title"],
         "summary":x["summary"][:400],
         "date_published":x["published_date"]+"T00:00:00+09:00",
         "tags":[t["label"] for t in x["technologies"]]
      } for x in cat["advisories"] if x["published_date"]==report["date"]][:100]
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return cat
