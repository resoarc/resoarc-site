#!/usr/bin/env python3
# Trigger the standard public single-site Internet.nl test, no batch API.
import re,time
from playwright.sync_api import sync_playwright
url="https://internet.nl/site/resoarc.com/"
with sync_playwright() as p:
    browser=p.chromium.launch(channel="msedge",headless=True)
    page=browser.new_page()
    try:
        page.goto(url,wait_until="domcontentloaded",timeout=30000)
        print("INITIAL",page.url,page.title(),flush=True)
        for i in range(42):
            page.wait_for_timeout(5000)
            if re.search(r"/site/resoarc\.com/\d+/?",page.url):
                print("RESULT_URL",page.url,flush=True)
                txt=page.locator("body").inner_text(timeout=9000)
                print("RESULT_BODY",re.sub(r"\s+"," ",txt)[:6000],flush=True)
                break
            if i%5==0:print("WAIT",i*5,"URL",page.url,flush=True)
        else:
            print("NOT_FINISHED",page.url,flush=True)
    finally:
        browser.close()
