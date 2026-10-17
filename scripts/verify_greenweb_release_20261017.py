#!/usr/bin/env python3
import requests,hashlib,json
from bs4 import BeautifulSoup
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"site"
s=requests.Session()
s.headers.update({"User-Agent":"ResoArc-Release-Verification/1.0"})
pages={"/":("Green Web Foundation","rec-green-card"),"/recognition/":("Green Web Foundation","rec-green-audit-value"),"/releases/":("Green Web Foundation","GREEN WEB"),"/os/":("ResoArcOS",None),"/products/":("無料ツール",None),"/source/":("ソース",None)}
for route,(text,cl) in pages.items():
    r=s.get("https://resoarc.com"+route,timeout=14)
    r.raise_for_status()
    ok=(text.lower() in r.text.lower()) and (not cl or cl in r.text)
    print("SITE",route,r.status_code,len(r.content),"PASS" if ok else "FAIL")
    if not ok:raise RuntimeError("live page text missing "+route)
    if route=="/":
        h=BeautifulSoup(r.content,"html.parser")
        green=h.select(".rec-green-card")
        assert len(green)==1,len(green)
        assert len(h.select(".rec-hub-quality-grid > article"))==4
        print("CARDS",len(h.select(".rec-hub-quality-grid > article")))
badge=s.get("https://resoarc.com/assets/recognition/green-web-verified-20261017.png",timeout=14)
badge.raise_for_status()
local=(p/"assets/recognition/green-web-verified-20261017.png").read_bytes()
assert local==badge.content
print("BADGE",len(local),hashlib.sha256(local).hexdigest()[:12],"MATCH")
evidence=s.get("https://api.thegreenwebfoundation.org/api/v3/greencheck/resoarc.com",timeout=14).json()
assert evidence["green"] is True
print("EVIDENCE",evidence["green"],evidence.get("hosted_by"))
# External scans. Do not publish unconfirmed scores.
checks={"INTERNETNL":"https://internet.nl/site/probes/resoarc.com/","SSL_LABS":"https://api.ssllabs.com/api/v3/analyze?host=resoarc.com&fromCache=on&maxAge=24","LIGHTHOUSE":"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https%3A%2F%2Fresoarc.com%2F&category=performance","BEST_PRACTICES":"https://www.bestpractices.dev/en/projects/15597"}
for name,url in checks.items():
    try:
        r=s.get(url,timeout=12)
        body=r.text
        print("SCAN",name,r.status_code,r.url[:150],len(body),body[:160].replace("\n"," "))
        if name=="SSL_LABS" and r.ok:
            j=r.json()
            print("SSL_RESULT",j.get("status"),[(v.get("ipAddress"),v.get("grade")) for v in j.get("endpoints",[])])
        if name=="BEST_PRACTICES" and r.ok:
            h=BeautifulSoup(body,"html.parser")
            print("BEST_PRACTICES_TITLE",h.title.get_text(" ",strip=True) if h.title else "none")
    except Exception as e:print("SCAN_ERROR",name,repr(e)[:250])
print("SITE_VERIFIED")
