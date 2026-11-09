#!/usr/bin/env python3
"""Current-site browser acceptance, separate from immutable historical snapshots.
Exercises public 16-product catalog and new postal v1.0.1 page at four widths.
"""
import json
import hashlib
import threading
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(("127.0.0.1",0),partial(Quiet,directory=str(SITE)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f"http://127.0.0.1:{server.server_port}"
expected="08a48b005749bf6a38583bfb2823a7b83c930c34140a133cf041b1d48b5ae148"
filename="resoarc-postal-address-v1.0.1-20261109.zip"
signed=SITE/"downloads"/filename
assert signed.is_file() and hashlib.sha256(signed.read_bytes()).hexdigest()==expected
assert (SITE/"downloads/resoarc-postal-address-v1.0.1-source.zip").is_file()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  try:
   for width in (320,390,768,1280):
    page=browser.new_page(viewport={"width":width,"height":844})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    response=page.goto(url+"/products/kintone/",wait_until="networkidle")
    assert response and response.status==200
    assert page.locator("article.kc-product").count()==16
    link=page.locator('a[href="/products/kintone/postal-address/"]')
    assert link.count()>=1
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2"),("catalog",width)
    response=page.goto(url+"/products/kintone/postal-address/",wait_until="networkidle")
    assert response and response.status==200
    assert page.locator("main").count()==1
    assert page.locator('a[href*="'+filename+'"]').count()>=1
    assert page.locator('a[href*="resoarc-postal-address-v1.0.1-source.zip"]').count()>=1
    assert expected in page.content()
    assert "zipcloud" not in page.locator("body").inner_text().lower()
    assert "日本郵便" in page.locator("body").inner_text()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2"),("postal page",width)
    assert not errors,(width,errors)
    print("CURRENT_POSTAL_BROWSER_PASS",width,flush=True)
    page.close()
  finally:browser.close()
finally:server.shutdown();server.server_close()
print("CURRENT_POSTAL_RELEASE_BROWSER_PASS 4 widths 16 products signed SHA-256 pinned")
