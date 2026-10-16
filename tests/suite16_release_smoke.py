#!/usr/bin/env python3
"""Smoke test all 16 catalog endpoints and signed QA download routes at two viewports."""
import json,functools
from pathlib import Path
from threading import Thread
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
ROUTES=[
"kintone-auto-number","kintone-tabs","kintone-conditional","kintone-conditional-format",
"kintone-date-calculator","kintone-list-search","kintone-grid-editor","kintone-kanban",
"kintone-bulk-preview","kintone-app-diff","kintone-permission-audit","kintone-import-check",
"kintone-duplicates","kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report"]
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'site')))
thread=Thread(target=srv.serve_forever,daemon=True);thread.start()
base='http://127.0.0.1:'+str(srv.server_address[1])
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width in [390,1280]:
   page=browser.new_page(viewport={'width':width,'height':844})
   for slug in ROUTES:
    url=base+'/tools/'+slug+'/'
    response=page.goto(url,wait_until='domcontentloaded',timeout=25000)
    assert response and response.status==200,(slug,response.status if response else None)
    assert page.locator('main').count()>=1,slug
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 7'),(slug,width)
   qa=page.goto(base+'/products/kintone/qa/',wait_until='domcontentloaded')
   assert qa.status==200
   assert '本番投入禁止' in page.content()
   info=json.loads(page.request.get(base+'/downloads/resoarc-signed-qa-manifest.json').text())
   assert len(info['plugins'])==8
   import hashlib
   for entry in info['plugins']:
    link=page.locator('a[href="/downloads/'+entry['filename']+'"]')
    assert link.count()==1,entry['slug']
    resource=page.request.get(base+'/downloads/'+entry['filename'])
    assert resource.status==200
    assert hashlib.sha256(resource.body()).hexdigest()==entry['sha256']
   print('PASS',width,'16 feature pages + signed QA downloads all hashes match')
   page.close()
  browser.close()
finally:
 srv.shutdown()
print('SUITE16_BROWSER_RELEASE_PASS')
