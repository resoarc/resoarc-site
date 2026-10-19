#!/usr/bin/env python3
"""Generate ResoArc navigation using the public sitemap as the single source of truth.

Physical HTML pages that are intentionally unlisted remain operational but NEVER
appear in public navigation; noindex pages are likewise hidden.
"""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
import json,re,sys

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
SCRIPT='<script defer src="/assets/navigation.js"></script>'
STYLE='<link rel="stylesheet" href="/assets/navigation.css">'
BASE='https://resoarc.com'
NAV_MAP=SITE/'assets/navigation-map.json'
EXCLUDE={'404.html'}
# Existing historic, unlisted alpha/beta material. New unlisted indexable pages
# raise a QA error until someone marks them noindex or adds them to the sitemap.
LEGACY_UNLISTED={
 '/tools/kintone-conditional/','/tools/kintone-tabs/',
}
LABELS={
 '/':'ホーム','/education/':'初学者教育支援',
 '/education/circuit/':'電子回路','/education/programming/':'ロボットプログラミング',
 '/products/':'無料ツール','/products/kintone/':'kintoneプラグイン',
 '/products/web/':'Webツール','/products/web/screens/':'画面キャプチャ',
 '/project/':'ResoArcについて','/principles/':'品質方針','/guide/':'利用ガイド',
 '/license/':'ライセンス','/privacy/':'プライバシー','/terms/':'利用条件',
 '/trust/':'信頼性と説明責任','/source/':'公開ソース',
 '/recognition/':'実績・協賛','/releases/':'更新履歴',
 '/os/':'ResoArcOS','/os/pi/':'Raspberry Pi版',
 '/products/roadmap/':'開発ロードマップ',
}
class TitleReader(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True)
  self.capture=None;self.h1='';self.title='';self.robots=''
 def handle_starttag(self,tag,attrs):
  props=dict(attrs)
  if tag in ('title','h1'):self.capture=tag
  if tag=='meta' and props.get('name','').lower()=='robots':
   self.robots=props.get('content','').lower()
 def handle_endtag(self,tag):
  if self.capture==tag:self.capture=None
 def handle_data(self,data):
  if self.capture=='h1':self.h1+=data
  if self.capture=='title':self.title+=data
def url_for(rel):
 return '/' if rel=='index.html' else '/'+(rel[:-len('index.html')] if rel.endswith('/index.html') else rel)
def sitemap_urls():
 doc=ET.parse(SITE/'sitemap.xml')
 urls=set()
 for loc in doc.findall('.//{*}loc'):
  if loc.text is None:continue
  parsed=urlparse(loc.text.strip())
  if parsed.scheme!='https' or parsed.netloc!='resoarc.com':
   raise ValueError('Unexpected sitemap host '+str(loc.text))
  urls.add(parsed.path)
 return urls
def title_for(url,doc):
 title=LABELS.get(url)
 if not title and (url.startswith('/products/kintone/') or url.startswith('/tools/')):
  title=doc.h1
 if not title:
  title=doc.title.split('|')[0].split('｜')[0].strip() or doc.h1 or url
 # Product pages with generic title should use a stable short visible heading.
 return re.sub(r'\s+',' ',title).strip()[:42]
def parent_for(url,available,public_web):
 if url=='/':return None
 if url.startswith('/tools/'):
  if url=='/tools/kintone-auto-number/':return '/products/kintone/'
  if url in public_web:return '/products/web/'
  return '/products/'
 parts=[x for x in url.strip('/').split('/') if x]
 for idx in range(len(parts)-1,0,-1):
  maybe='/'+ '/'.join(parts[:idx])+'/'
  if maybe in available:return maybe
 return '/'
def main():
 files=sorted(SITE.rglob('*.html'))
 sm=sitemap_urls()
 # Root source listing of officially published free web tools
 catalog=(SITE/'products/web/index.html').read_text(encoding='utf8')
 public_web=set(re.findall(r'href="(/tools/[a-z0-9-]+/)"',catalog))
 pages={};indexable_not_listed=[]
 for file in files:
  rel=file.relative_to(SITE).as_posix()
  if rel in EXCLUDE:continue
  url=url_for(rel)
  source=file.read_text(encoding='utf8')
  parsed=TitleReader();parsed.feed(source)
  noindex='noindex' in parsed.robots
  if url in sm and noindex:raise ValueError('Sitemap contains noindex page: '+url)
  if url not in sm and not noindex and url not in LEGACY_UNLISTED:
   indexable_not_listed.append(url)
  pages[url]={'title':title_for(url,parsed),'parent':None,'visible':url in sm and not noindex}
 if indexable_not_listed:
  raise ValueError('New pages must be in sitemap or explicitly noindex: '+str(indexable_not_listed))
 if len(sm)!=len({k for k,v in pages.items() if v['visible']}):
  raise ValueError('Public sitemap and navigation disagree')
 for url,entry in pages.items():
  entry['parent']=parent_for(url,pages,public_web)
  if entry['parent'] is not None and entry['parent'] not in pages:
   raise ValueError('Missing parent '+url)
  if entry['visible'] and entry['parent'] and not pages[entry['parent']]['visible']:
   raise ValueError('Hidden ancestor on public page '+url)
 manifest={'version':2,'pages':pages}
 NAV_MAP.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 injected=0
 for file in files:
  rel=file.relative_to(SITE).as_posix()
  if rel in EXCLUDE:continue
  html=file.read_text(encoding='utf8')
  changed=False
  if STYLE not in html:
   if '</head>' not in html:raise ValueError('Missing closing head '+rel)
   html=html.replace('</head>',STYLE+'</head>',1)
   changed=True
  if SCRIPT not in html:
   if '</body>' not in html:raise ValueError('Missing closing body '+rel)
   html=html.replace('</body>',SCRIPT+'</body>',1)
   changed=True
  if html.count(STYLE)!=1 or html.count(SCRIPT)!=1:raise ValueError('Duplicate navigation resource '+rel)
  if changed:
   file.write_text(html,encoding='utf8',newline='\n')
   injected+=1
 print(f'NAV_BUILD_PASSED total={len(pages)} public={len(sm)} hidden={len(pages)-len(sm)} injected={injected}')
if __name__=='__main__':main()
