# SPDX-FileCopyrightText: 2026 ResoArc contributors
# SPDX-License-Identifier: MIT
"""Browser regression for product-category navigation, filters, and mobile layout."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from functools import partial
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass

def main(input):
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(SITE)))
 Thread(target=server.serve_forever,daemon=True).start()
 base='http://127.0.0.1:'+str(server.server_port)
 checks=[]
 errors=[]
 try:
  with sync_playwright() as p:
   try:b=p.chromium.launch(headless=True)
   except:b=p.chromium.launch(headless=True,channel='msedge')
   try:
    for width in (1440,390):
     page=b.new_page(viewport={'width':width,'height':860})
     page.on('pageerror',lambda exc:errors.append(str(exc)))
     for route in ('/','/products/','/products/kintone/','/products/web/','/products/web/qaiuick/'):
      resp=page.goto(base+route,wait_until='domcontentloaded',timeout=20000)
      assert resp.status==200,(route,resp.status)
      page.locator('.ra-menu-group').first.wait_for(timeout=12000)
      assert page.locator('.ra-menu-group').count()==5,route
      overflow=page.evaluate('document.documentElement.scrollWidth - innerWidth')
      assert overflow<=2,(route,width,'overflow',overflow)
      if route=='/products/':
       assert page.locator('.ra-discovery-card').count()==5
      if route=='/products/kintone/':
       assert page.locator('.kc-product').count()==16
       assert page.locator('.kc-category-section').count()==4
       assert page.locator('.kc-product:visible').count()==16
       page.locator('.kc-filter-buttons button[data-category="一覧・データ"]').click()
       assert page.locator('.kc-product:visible').count()==3
       page.locator('#kc-search').fill('CSV')
       assert page.locator('.kc-product:visible').count()==1
       page.locator('#kc-search').fill('')
       page.locator('.kc-filter-buttons button[data-category="すべて"]').click()
       assert page.locator('.kc-product:visible').count()==16
      if route=='/products/web/':
       assert page.locator('.ra-web-group').count()==4
       assert page.locator('.ra-web-group article.product-card').count()==11
      if route=='/products/web/qaiuick/':
       if width==1440:
        page.locator('.ra-sidebar-search').fill('ルックアップ')
        assert page.locator('.ra-node a[href="/products/kintone/lookup-suggest/"]:visible').count()==1
        page.locator('.ra-sidebar-search').fill('')
        assert page.locator('.ra-menu-group').count()==5
      checks.append(f'{width}px {route}')
     if width==390:
      page.locator('.ra-nav-toggle').click()
      assert page.locator('body.ra-drawer-open').count()==1
      assert page.locator('.ra-sidebar').is_visible()
      page.locator('.ra-sidebar-close').click()
      assert page.locator('body.ra-drawer-open').count()==0
     page.close()
    assert not errors,errors
   finally:b.close()
 finally:
  server.shutdown();server.server_close()
 return {'passed':len(checks),'cases':checks,'js_errors':errors}
