#!/usr/bin/env python3
"""Capture live site changes before editing, preserving immutable Web8 release files.
This is an emergency synchronisation while upstream GitHub is unavailable.
"""
from pathlib import Path
from urllib.parse import urlparse,unquote
from concurrent.futures import ThreadPoolExecutor,as_completed
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests,hashlib,re

SITE=Path(__file__).resolve().parents[1]/"site"
BASE="https://resoarc.com"
session=requests.Session()
session.headers.update({"User-Agent":"ResoArc-site-integrity-review/1.0"})
sitemap=session.get(BASE+"/sitemap.xml",timeout=15);sitemap.raise_for_status()
routes=[x.text for x in ET.fromstring(sitemap.content).iter() if x.tag.endswith('loc')]
paths={}
for u in routes:
 p=urlparse(u).path
 if not p.startswith('/'):continue
 paths[(p+"index.html" if p.endswith("/") else p).lstrip("/")]=u
for name in ("404.html","llms.txt","robots.txt","sitemap.xml"):
 paths[name]=BASE+"/"+name
# Live HTML may refer to newly deployed same-origin static assets missing from old checkout.
def load(x):
 name,url=x
 try:
  res=session.get(url,timeout=18)
  if res.status_code!=200: return name,url,None,"HTTP "+str(res.status_code)
  if name.endswith(".html") and "text/html" not in res.headers.get('content-type',''):
   return name,url,None,"unexpected MIME "+res.headers.get('content-type','')
  return name,url,res.content,None
 except Exception as e:return name,url,None,str(e)
with ThreadPoolExecutor(max_workers=8) as pool:
 first=list(pool.map(load,paths.items()))
for name,url,data,error in first:
 if error:raise RuntimeError(name+": "+error)
 if name.endswith('.html'):
  doc=BeautifulSoup(data,'html.parser')
  for tag in doc.find_all(['link','script','img','source']):
   src=tag.get('href') if tag.name=='link' else tag.get('src')
   if not src or not src.startswith('/'):continue
   if src.startswith('//'):continue
   path=urlparse(src).path.lstrip('/')
   if not path or path.endswith('/') or path in paths:continue
   paths[path]=BASE+"/"+path
# CSS imports / url entries: pull just absent assets.
for name,url,data,error in first:
 if name.endswith('.html'):continue
# Protect exact eight frozen GA pages.
IMMUTABLE={f"tools/{s}/index.html" for s in (
 "kintone-bulk-preview","kintone-app-diff","kintone-permission-audit","kintone-import-check",
 "kintone-duplicates","kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report"
)}
changes=[];unchanged=[];failures=[]
def process(result):
 name,url,data,error=result
 if error:return ("error",name,error)
 file=SITE/name
 before=file.read_bytes() if file.exists() else None
 if name in IMMUTABLE and before!=data:
  return ("frozen",name,"immutable production Web8 file differs from local checksum")
 if before==data:return ("same",name,"")
 file.parent.mkdir(parents=True,exist_ok=True)
 file.write_bytes(data)
 return ("update",name,("NEW" if before is None else "MODIFIED")+" bytes "+str(len(data)))
with ThreadPoolExecutor(max_workers=8) as pool:
 for tup in pool.map(load,paths.items()):
  state,name,msg=process(tup)
  if state in ("error","frozen"):failures.append((state,name,msg))
  elif state=="update":changes.append((name,msg))
  else:unchanged.append(name)
if failures:raise RuntimeError("SYNC FAILURES: "+str(failures))
# CSS-level referenced assets (fonts etc).
for css in SITE.rglob('*.css'):
 txt=css.read_text(encoding="utf8")
 for path in re.findall(r'url\([\'\"]?(/assets/[^)\'\"]+)',txt):
  target=SITE/path.lstrip('/')
  if target.exists():continue
  resp=session.get(BASE+path,timeout=12)
  if resp.status_code!=200:raise RuntimeError("CSS asset missing "+path)
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(resp.content)
  changes.append((path,"CSS asset restored"))
print("LIVE_SNAPSHOT",len(routes),"routes",len(paths),"total HTTP assets",len(changes),"changes",len(unchanged),"unchanged")
for row in changes:print("UPDATED",*row)
