#!/usr/bin/env python3
import sys
from playwright.sync_api import sync_playwright
url=(sys.argv[1] if len(sys.argv)>1 else "https://recognition-perf-20261018.resoarc.pages.dev").rstrip("/")
with sync_playwright() as p:
    b=p.chromium.launch(channel="msedge",headless=True)
    for w in (390,1000,1440):
        c=b.new_context(viewport={"width":w,"height":900},device_scale_factor=1)
        page=c.new_page()
        page.goto(url+"/",wait_until="networkidle",timeout=25000)
        img=page.locator("main#main > section.hero > div.hero-visual > img")
        assert img.count()==1
        src=img.evaluate("(x)=>x.currentSrc")
        dims=img.evaluate("(x)=>[x.naturalWidth,x.naturalHeight,x.complete]")
        assert ".webp" in src and dims[2] and dims[0]>0,(w,src,dims)
        cards=page.locator(".rec-hub-quality-grid > article").count()
        assert cards==6,(w,cards)
        scroll=page.evaluate("document.documentElement.scrollWidth")
        client=page.evaluate("document.documentElement.clientWidth")
        assert scroll<=client+2,(w,scroll,client)
        print("RESPONSIVE_OK",w,"image",src.split("/")[-1],"dims",dims[:2],"quality_cards",cards,flush=True)
        c.close()
    b.close()
