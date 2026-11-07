#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Real local static-site browser smoke: 3 engines x 2 viewports x catalog+3 details."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

site=Path(__file__).resolve().parents[1]/"site"
slugs={
 "input-template":"入力テンプレート",
 "reuse-reset":"レコード再利用制御",
 "mail-compose":"メール作成ボタン",
}
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

server=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(site)))
Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}"
success=0
try:
 with sync_playwright() as p:
  for engine in ("chromium","firefox","webkit"):
   browser=getattr(p,engine).launch(headless=True)
   try:
    for width in (390,1440):
     page=browser.new_page(viewport={"width":width,"height":900},device_scale_factor=1)
     errors=[]
     page.on("pageerror",lambda e:errors.append(str(e)))
     try:
      for slug,title in [("","kintone"),*slugs.items()]:
       url=("/products/kintone/" if not slug else f"/products/kintone/{slug}/")
       response=page.goto(base+url,wait_until="domcontentloaded",timeout=25000)
       assert response and response.status==200,(engine,width,url,"http")
       assert title in page.locator("h1").inner_text(),(engine,width,url,"h1")
       page.wait_for_timeout(120)
       overflow=page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
       assert overflow<=3,(engine,width,url,"horizontal overflow",overflow)
       broken=page.locator("img").evaluate_all("(images) => images.filter(i => i.complete && i.naturalWidth===0).map(i=>i.src)")
       assert not broken,(engine,width,url,"broken images",broken)
       assert not errors,(engine,width,url,"pageerror",errors)
       if slug:
        links=page.locator(f'a[href^="/downloads/resoarc-{slug}-v1.0.0-"]')
        assert links.count()>0,(engine,width,url,"package link")
       else:
        assert page.locator("article.kc-product").count()==15,(engine,width,url,"catalog count")
        page.locator("button[data-category='入力・設定']").click()
        page.wait_for_timeout(100)
        for s in slugs:
         assert page.locator(f'article.kc-product:has(a[href="/products/kintone/{s}/"])').is_visible(),(engine,width,s,"filter")
        page.locator("button[data-category='すべて']").click()
       success+=1
      print("PASS",engine,width,"catalog+3 detail pages")
     finally:
      page.close()
   finally:
    browser.close()
finally:
 server.shutdown()
print("BROWSER_RELEASE_PASS",success,"of",24,"page/viewports","3 engines")
assert success==24
