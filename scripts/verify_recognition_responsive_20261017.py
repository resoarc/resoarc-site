from collections import Counter
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(channel="msedge",headless=True)
    for width in (1440,1000,390):
        page=b.new_page(viewport={"width":width,"height":900})
        for route,selector in (("/",".rec-hub-quality-grid > article"),("/recognition/",".rec-audit-grid-5 > article")):
            page.goto("https://resoarc.com"+route,wait_until="domcontentloaded",timeout=18000)
            boxes=[e.bounding_box() for e in page.locator(selector).all()]
            assert len(boxes)==6,(width,route,len(boxes))
            rows=sorted(Counter(round(x["y"]) for x in boxes).values())
            expected={1440:[3,3],1000:[2,2,2],390:[1,1,1,1,1,1]}[width]
            assert rows==expected,(width,route,rows)
            print("LAYOUT_OK",width,route,rows,flush=True)
        page.close()
    b.close()
