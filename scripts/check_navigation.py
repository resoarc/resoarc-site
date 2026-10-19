#!/usr/bin/env python3
"""Fail a release when navigation map, pages, or public sitemap drift."""
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from html.parser import HTMLParser
import json,sys
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
SCRIPT='<script defer src="/assets/navigation.js"></script>'
STYLE='<link rel="stylesheet" href="/assets/navigation.css">'
NAV=SITE/'assets/navigation-map.json'
class Robot(HTMLParser):
 def __init__(self):super().__init__();self.robots=''
 def handle_starttag(self,tag,attrs):
  v=dict(attrs)
  if tag=='meta' and v.get('name')=='robots':self.robots=v.get('content','')
def path_for(rel):
 return '/' if rel=='index.html' else '/'+(rel[:-len('index.html')] if rel.endswith('/index.html') else rel)
def main():
 errors=[]
 data=json.loads(NAV.read_text(encoding='utf8'))
 pages=data['pages'];sm=set()
 for x in ET.parse(SITE/'sitemap.xml').findall('.//{*}loc'):
  if x.text:sm.add(urlparse(x.text).path)
 for f in SITE.rglob('*.html'):
  rel=f.relative_to(SITE).as_posix()
  if rel=='404.html':continue
  url=path_for(rel);s=f.read_text(encoding='utf8')
  if s.count(SCRIPT)!=1:errors.append(f'Navigation script count invalid: {rel}')
  if s.count(STYLE)!=1:errors.append(f'Navigation stylesheet count invalid: {rel}')
  if url not in pages:errors.append(f'Unregistered page: {url}');continue
  doc=Robot();doc.feed(s)
  if ('noindex' in doc.robots or url not in sm) and pages[url]['visible']:
   errors.append(f'Unreleased or noindex page exposed: {url}')
  if url in sm and not pages[url]['visible']:errors.append(f'Published page missing in menu: {url}')
  if url in sm and 'noindex' in doc.robots:errors.append(f'Sitemap lists noindex page: {url}')
 for url,info in pages.items():
  rel='index.html' if url=='/' else url.lstrip('/')+'index.html' if url.endswith('/') else url.lstrip('/')
  if not (SITE/rel).is_file():errors.append('Stale page '+url)
  if info['parent'] and info['parent'] not in pages:errors.append('Missing parent '+url)
  if info['visible'] and info['parent'] and not pages[info['parent']]['visible']:errors.append('Hidden public ancestor '+url)
 if len(sm)!=sum(bool(x['visible']) for x in pages.values()):errors.append('Public sitemap count disagrees with navigation')
 if data.get('version')!=2:errors.append('Wrong nav manifest version')
 if len(pages)<42:errors.append('Unexpected page count')
 # Guarantee output is exactly what a fresh build would write: UI generation cannot forget new pages.
 from subprocess import run,PIPE
 import hashlib
 files=[NAV,*sorted(SITE.rglob('*.html'))]
 pre={p.relative_to(SITE).as_posix():hashlib.sha256(p.read_bytes()).digest() for p in files}
 proc=run([sys.executable,str(ROOT/'scripts/build_navigation.py')],cwd=str(ROOT),stdout=PIPE,stderr=PIPE,text=True)
 if proc.returncode!=0:errors.append('Generator failed: '+proc.stderr[-350:])
 else:
  for p in files:
   if hashlib.sha256(p.read_bytes()).digest()!=pre[p.relative_to(SITE).as_posix()]:
    errors.append('Generator not idempotent: '+str(p.relative_to(SITE)))
 print(f'NAV_CHECK total={len(pages)} public={len(sm)} errors={len(errors)}')
 for e in errors[:30]:print('NAV_ERROR',e)
 return bool(errors)
if __name__=='__main__':sys.exit(main())
