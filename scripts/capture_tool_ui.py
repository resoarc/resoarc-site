#!/usr/bin/env python3
"""Capture real local web tool interfaces and explicitly labelled kintone-config test previews."""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from io import BytesIO
import json
import threading

from PIL import Image, ImageOps
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"site/assets/tool-screens"
OUT.mkdir(parents=True,exist_ok=True)
WEB=(
    "hash","csv","kintone-app-diff","kintone-import-check",
    "kintone-bulk-preview","kintone-permission-audit",
    "kintone-duplicates","kintone-lookup-audit",
    "kintone-cross-aggregate","kintone-print-report",
)
PLUGINS=(
    "kintone-auto-number","kintone-tabs","kintone-conditional","kintone-conditional-format",
    "kintone-date-calculator","kintone-list-search","kintone-grid-editor","kintone-kanban",
)
CONFIG_ROOT={
    "kintone-auto-number":"plugins/auto-number/src",
    "kintone-tabs":"plugins/tabs/v0.1.0-beta/src",
    "kintone-conditional":"plugins/conditional/v0.1.0-alpha/src",
    "kintone-conditional-format":"plugins/conditional-format/v0.1.0-alpha/src",
    "kintone-date-calculator":"plugins/date-calculator/v0.1.0-alpha/src",
    "kintone-list-search":"plugins/list-search/v0.1.0-alpha/src",
    "kintone-grid-editor":"plugins/grid-editor/v0.1.0-alpha/src",
    "kintone-kanban":"plugins/kanban/v0.1.0-alpha/src",
}
FIELDS={
    "InvoiceNumber":{"type":"SINGLE_LINE_TEXT","label":"請求番号","code":"InvoiceNumber"},
    "Name":{"type":"SINGLE_LINE_TEXT","label":"案件名","code":"Name"},
    "Notes":{"type":"SINGLE_LINE_TEXT","label":"備考","code":"Notes"},
    "Title":{"type":"SINGLE_LINE_TEXT","label":"タイトル","code":"Title"},
    "risk":{"type":"NUMBER","label":"リスクスコア","code":"risk"},
    "amount":{"type":"NUMBER","label":"金額","code":"amount"},
    "Amount":{"type":"NUMBER","label":"金額","code":"Amount"},
    "start_date":{"type":"DATE","label":"開始日","code":"start_date"},
    "end_date":{"type":"DATE","label":"終了日","code":"end_date"},
    "duration":{"type":"NUMBER","label":"期間","code":"duration"},
    "Status":{"type":"DROP_DOWN","label":"ステータス","code":"Status"},
}
class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self,*_args):pass

MOCK_INIT="""(fields)=>{
  window.kintone={
     $PLUGIN_ID:'resoarc-preview',
     plugin:{app:{getConfig:()=>({}),setConfig:(cfg,done)=>{window._previewSettings=cfg; if(done)done();}}},
     app:{getId:()=>123,getFormFields:async()=>fields},
     api:Object.assign(async()=>({properties:fields}),{url:(url)=>url}),
  };
  window.cybozu={};
  window.confirm=()=>true;
}"""

def capture(page,slug:str):
    data=page.screenshot(type="png",full_page=False,animations="disabled")
    image=Image.open(BytesIO(data)).convert("RGB")
    image=ImageOps.fit(image,(1120,710),method=Image.Resampling.LANCZOS)
    image.save(OUT/(slug+".webp"),format="WEBP",quality=82,method=6)
    return (OUT/(slug+".webp")).stat().st_size

def one_web(browser,slug,host):
    page=browser.new_page(viewport={"width":1280,"height":812},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    try:
        page.goto(host+"/tools/"+slug+"/",wait_until="domcontentloaded",timeout=20000)
        page.wait_for_timeout(350)
        # Demonstrate the real parser against deliberately fictitious, safe sample data.
        try:
            if slug == "hash":
                page.locator("#hash-file").set_input_files({"name":"sample.txt","mimeType":"text/plain","buffer":b"ResoArc test data"})
                page.locator("#hash-go").click()
                page.wait_for_timeout(500)
            elif slug == "csv":
                page.locator("#csv-file").set_input_files({"name":"sample.csv","mimeType":"text/csv","buffer":"name,amount\nA,120\nB,240\n".encode("utf-8")})
                page.locator("#csv-run").click()
                page.wait_for_timeout(500)
            elif slug == "kintone-app-diff":
                for selector,data in [("#diff-before",'{"properties":{"name":{"type":"SINGLE_LINE_TEXT"}}}'),
                                      ("#diff-after",'{"properties":{"name":{"type":"SINGLE_LINE_TEXT"},"amount":{"type":"NUMBER"}}}')]:
                    page.locator(selector).set_input_files({"name":"form.json","mimeType":"application/json","buffer":data.encode("utf-8")})
                page.locator("#diff-run").click()
                page.wait_for_timeout(500)
            elif slug == "kintone-import-check":
                schema={"properties":{"name":{"code":"name","label":"氏名","type":"SINGLE_LINE_TEXT","required":True},
                                      "amount":{"code":"amount","label":"金額","type":"NUMBER","required":True}}}
                page.locator("#import-csv").set_input_files({"name":"sample.csv","mimeType":"text/csv","buffer":"name,amount\n田中,120\n佐藤,240\n".encode("utf-8")})
                page.locator("#import-form").set_input_files({"name":"form.json","mimeType":"application/json","buffer":json.dumps(schema,ensure_ascii=False).encode("utf-8")})
                page.locator("#import-run").click()
                page.wait_for_timeout(600)
            elif slug in ("kintone-bulk-preview","kintone-permission-audit","kintone-duplicates",
                          "kintone-lookup-audit","kintone-cross-aggregate","kintone-print-report"):
                cases={
                  "kintone-bulk-preview":('[{"id":"1","status":"new"}]','[{"id":"1","status":"done"}]'),
                  "kintone-permission-audit":('{"rights":[{"entity":{"code":"team"},"viewRecord":true}]}',None),
                  "kintone-duplicates":('[{"name":"A","email":"x"},{"name":"a","email":"x"}]',None),
                  "kintone-lookup-audit":('[{"code":"C1","name":"wrong"}]','[{"code":"C1","name":"real"}]'),
                  "kintone-cross-aggregate":('[{"department":"X","amount":"10"},{"department":"X","amount":"20"}]',None),
                  "kintone-print-report":('[{"name":"A","amount":"22"}]',None),
                }
                primary,secondary=cases[slug]
                page.locator("#suite-primary").set_input_files({"name":"sample.json","mimeType":"application/json","buffer":primary.encode("utf-8")})
                if secondary:
                    page.locator("#suite-secondary").set_input_files({"name":"comparison.json","mimeType":"application/json","buffer":secondary.encode("utf-8")})
                page.locator("#suite-run").click()
                page.wait_for_function("document.getElementById('suite-state').textContent.startsWith('完了')",timeout=7000)
        except Exception as exc:
            print("CAPTURE_SAMPLE_WARNING",slug,str(exc)[:180])
        # The subject is the working interface, not the overview hero or the new screenshot.
        target=page.locator(".tool-shell").first if page.locator(".tool-shell").count() else page.locator("main .inner-section").first
        target.scroll_into_view_if_needed(timeout=5000)
        page.evaluate("window.scrollBy(0,-50)")
        page.wait_for_timeout(150)
        size=capture(page,slug)
        print("WEB_CAPTURE",slug,size,"bytes","pageErrors",len(errors))
    finally:
        page.close()

def one_plugin(browser,slug):
    folder=ROOT/CONFIG_ROOT[slug]
    page=browser.new_page(viewport={"width":1280,"height":812},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    try:
        page.set_content((folder/"html/config.html").read_text(encoding="utf-8"),wait_until="domcontentloaded")
        css=folder/"css/config.css"
        if css.exists():
            page.add_style_tag(content=css.read_text(encoding="utf-8"))
        page.evaluate(MOCK_INIT,FIELDS)
        core=folder/"js/core.js"
        config=folder/"js/config.js"
        if core.exists():
            page.add_script_tag(content=core.read_text(encoding="utf-8"))
        if config.exists():
            page.add_script_tag(content=config.read_text(encoding="utf-8"))
        page.wait_for_timeout(450)
        # Capture the plugin's actual published configuration markup. Test context is not a tenant.
        page.evaluate("window.scrollTo(0,0)")
        size=capture(page,slug)
        visible=len(page.locator("main input,main select,main button").all())
        print("PLUGIN_CAPTURE",slug,size,"bytes","controls",visible,"pageErrors",len(errors))
        if visible==0:
            raise RuntimeError(slug+": no actual plugin settings controls rendered")
    finally:
        page.close()

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(SilentHandler,directory=str(ROOT/"site")))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    host=f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            try:browser=playwright.chromium.launch(headless=True)
            except Exception: browser=playwright.chromium.launch(channel="msedge",headless=True)
            try:
                for slug in WEB:one_web(browser,slug,host)
                for slug in PLUGINS:one_plugin(browser,slug)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    files=list(OUT.glob("*.webp"))
    print("CAPTURE_COMPLETE",len(files),"files","totalBytes",sum(f.stat().st_size for f in files))
    assert len(files)==len(WEB)+len(PLUGINS)

if __name__=="__main__":
    main()
