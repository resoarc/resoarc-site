#!/usr/bin/env python3
"""Regression checks for the continuous kintone card grid and 18 genuine UI captures."""
from __future__ import annotations
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import re,threading
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
SLUGS=[p.parent.name for p in (SITE/"tools").glob("*/index.html")]
assert len(SLUGS)==18,SLUGS
WEB8={"kintone-bulk-preview","kintone-app-diff","kintone-permission-audit","kintone-import-check","kintone-duplicates","kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report"}
for slug in SLUGS:
    doc=BeautifulSoup((SITE/"tools"/slug/"index.html").read_text(encoding="utf-8"),"html.parser")
    figure=doc.select_one(".tool-preview-figure")
    if slug in WEB8:
        assert figure is None,slug  # release v1.0.0 source is immutable
    else:
        assert len(doc.select(".tool-preview-section"))==1 and figure is not None,slug
    image=SITE/"assets/tool-screens"/(slug+".webp")
    icon=SITE/"assets/tool-icons"/(slug+".svg")
    assert image.is_file() and icon.is_file(),slug
    assert image.stat().st_size>10000,slug
    with Image.open(image) as im:
        assert im.size==(1120,710),slug
        assert im.format=="WEBP",slug
    if figure:
        assert figure.select_one("img.tool-preview-image")["src"]=="/assets/tool-screens/"+slug+".webp",slug
    assert icon.read_text(encoding="utf-8").startswith("<svg "),slug
    if slug.startswith("kintone-") and slug not in (
        "kintone-app-diff","kintone-import-check","kintone-bulk-preview","kintone-permission-audit",
        "kintone-duplicates","kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report"
    ):
        assert "実際のkintoneテナントでの動作保証ではありません" in figure.get_text(),slug

gallery=BeautifulSoup((SITE/"products/web/screens/index.html").read_text(encoding="utf-8"),"html.parser")
assert len(gallery.select('.tool-gallery-item'))==8
for slug in WEB8:
    item=gallery.select_one('#'+slug)
    assert item and item.select_one('.tool-gallery-image')['src']=='/assets/tool-screens/'+slug+'.webp',slug
catalog=BeautifulSoup((SITE/"products/kintone/index.html").read_text(encoding="utf-8"),"html.parser")
grids=catalog.select(".product-grid")
assert len(grids)==1,len(grids)
assert len(grids[0].select(".product-card"))==8
assert len(grids[0].select(".tool-feature-icon"))==8
for name in ("index.html","kintone/index.html","kintone/qa/index.html","web/index.html"):
    page=BeautifulSoup((SITE/"products"/name).read_text(encoding="utf-8"),"html.parser")
    for card in page.select(".product-card"):
        icon=card.select_one(".tool-feature-icon")
        assert icon is not None,(name,card.get_text(" ",strip=True)[:30])

class NoLog(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

server=ThreadingHTTPServer(("127.0.0.1",0),partial(NoLog,directory=str(SITE)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    with sync_playwright() as p:
        try:b=p.chromium.launch(headless=True)
        except Exception:b=p.chromium.launch(channel="msedge",headless=True)
        try:
            for width in (1440,390):
                page=b.new_page(viewport={"width":width,"height":900})
                errors=[]
                page.on("pageerror",lambda exc:errors.append(str(exc)))
                base=f"http://127.0.0.1:{server.server_port}"
                page.goto(base+"/products/kintone/",wait_until="networkidle")
                assert not errors,errors
                assert page.locator(".product-grid .product-card").count()==8
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),"overflow"
                coords=page.locator(".product-grid .product-card").evaluate_all(
                    "(all)=>all.map(e=>({x:Math.round(e.getBoundingClientRect().x),y:Math.round(e.getBoundingClientRect().y)}))"
                )
                if width==1440:
                    assert all(coords[i]["y"]==coords[i+1]["y"] for i in range(0,8,2)),coords
                    assert all(coords[i]["y"]<coords[i+2]["y"] for i in range(0,6,2)),coords
                else:
                    assert all(coords[i]["y"]<coords[i+1]["y"] for i in range(7)),coords
                assert page.locator(".tool-feature-icon").first.evaluate(
                    "(el)=>el.complete && el.naturalWidth>0"
                )
                page.goto(base+"/products/web/screens/",wait_until="networkidle")
                assert page.locator('.tool-gallery-image').count()==8
                assert page.locator('.tool-gallery-image').first.evaluate('(el)=>el.complete&&el.naturalWidth>0')
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.goto(base+"/tools/kintone-grid-editor/",wait_until="networkidle")
                assert page.locator(".tool-preview-image").is_visible()
                assert page.locator(".tool-preview-image").evaluate(
                    "(el)=>el.complete && el.naturalWidth>0"
                )
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                assert not errors,errors
                page.close()
                print("CATALOG_MEDIA_OK",width,"cards",len(coords),"no gaps, image loaded")
        finally:b.close()
finally:
    server.shutdown()
    server.server_close()
print("CATALOG_MEDIA_PASS: 18 screenshots, 18 icons, 8-card grid")
