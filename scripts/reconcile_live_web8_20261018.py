#!/usr/bin/env python3
"""Recover newest live Web8 HTML during concurrent site updates, preserving tool JS and all existing behavior."""
from pathlib import Path
from bs4 import BeautifulSoup
import requests,hashlib
root=Path(__file__).resolve().parents[1]/"site/tools"
names=("kintone-bulk-preview","kintone-app-diff","kintone-permission-audit","kintone-import-check","kintone-duplicates","kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report")
s=requests.Session();s.headers.update({"User-Agent":"ResoArc-site-integrity-review/1.0"})
updates=[]
for n in names:
    local=root/n/"index.html"
    before=local.read_bytes()
    r=s.get("https://resoarc.com/tools/"+n+"/",timeout=15);r.raise_for_status()
    assert "text/html" in r.headers.get("content-type",""),n
    original=BeautifulSoup(before,"html.parser")
    newer=BeautifulSoup(r.content,"html.parser")
    oldjs=[x.get("src") for x in original.select("script[src]")]
    newjs=[x.get("src") for x in newer.select("script[src]")]
    assert oldjs==newjs,("tool JavaScript references changed",n,oldjs,newjs)
    assert original.select_one("main") and newer.select_one("main"),n
    if before!=r.content:
        local.write_bytes(r.content)
        updates.append(n)
print("WEB8_LIVE_RECONCILED",len(updates),"UPDATED",updates)
