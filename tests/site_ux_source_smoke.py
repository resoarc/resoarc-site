#!/usr/bin/env python3
"""Static-site regression for mobile overflow, source fallback, and frozen GA."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

SITE=Path(__file__).resolve().parents[1]/"site"
class Silent(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
server=ThreadingHTTPServer(("127.0.0.1",0),partial(Silent,directory=str(SITE)))
Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}"
cases=['/tools/kintone-auto-number/','/tools/kintone-conditional-format/','/tools/kintone-date-calculator/',
'/tools/kintone-kanban/','/tools/kintone-list-search/','/products/kintone/','/products/web/screens/','/source/','/','/releases/','/os/']
try:
 with sync_playwright() as p:
  try:b=p.chromium.launch(headless=True)
  except:b=p.chromium.launch(headless=True,channel="msedge")
  try:
   for width in (320,390,768,1440):
    page=b.new_page(viewport={"width":width,"height":880})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    for route in cases:
     res=page.goto(base+route,wait_until="networkidle")
     assert res.status==200,(width,route,res.status)
     overflow=page.evaluate("document.documentElement.scrollWidth - innerWidth")
     assert overflow<=1,(width,route,overflow)
     if route=='/source/':
      assert page.get_by_text('GitHub',exact=False).count()>0
      links=page.locator('main a[href^="/downloads/"]')
      assert links.count()>=8
      for a in links.all():
       href=a.get_attribute('href')
       assert (SITE/href.lstrip('/')).is_file(),href
     if route=='/products/kintone/':
      assert page.locator('.product-grid .product-card').count()==8
      assert '公開製品・開発版' in page.locator('main').inner_text()
     if route=='/releases/':
      assert 'スマートフォン表示の整合性' in page.locator('main').inner_text()
     if route in ['/tools/kintone-kanban/','/tools/kintone-date-calculator/']:
      pre=page.locator("pre.suite-result")
      assert pre.count()>0
      assert pre.first.evaluate("(el)=>getComputedStyle(el).overflowX==='auto'"),route
     assert not errors,(width,route,errors)
    page.close()
    print('UX_SOURCE_PASS',width,len(cases),'routes')
  finally:b.close()
finally:
 server.shutdown();server.server_close()
print('UX_SOURCE_SMOKE_PASS')
