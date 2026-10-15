"""Local browser smoke tests of ResoArc suite without external APIs."""
from pathlib import Path
from threading import Thread
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
from playwright.sync_api import sync_playwright
SITE = Path(__file__).resolve().parents[1] / 'site'
class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(SITE)))
thread = Thread(target=server.serve_forever,daemon=True)
thread.start()
base='http://127.0.0.1:'+str(server.server_port)
cases=[
 ('kintone-bulk-preview', '[{"id":"1","status":"new"}]', '[{"id":"1","status":"done"}]', 'changedRecords'),
 ('kintone-permission-audit','{"rights":[{"entity":{"code":"team"},"viewRecord":true}]}',None,'ruleCount'),
 ('kintone-duplicates','[{"name":"A","email":"x"},{"name":"a","email":"x"}]',None,'duplicateGroups'),
 ('kintone-lookup-audit','[{"code":"C1","name":"wrong"}]','[{"code":"C1","name":"real"}]','issueCount'),
 ('kintone-cross-aggregate','[{"department":"X","amount":"10"},{"department":"X","amount":"20"}]',None,'groups'),
 ('kintone-print-report','[{"name":"A","amount":"22"}]',None,'printReady'),
]
try:
 with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':390,'height':844})
    errors=[]
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    for route,primary,secondary,key in cases:
        response=page.goto(base+'/tools/'+route+'/',wait_until='networkidle')
        assert response.status==200,route
        page.locator('#suite-primary').set_input_files({'name':'primary.json','mimeType':'application/json','buffer':primary.encode('utf-8')})
        if secondary:
            page.locator('#suite-secondary').set_input_files({'name':'secondary.json','mimeType':'application/json','buffer':secondary.encode('utf-8')})
        page.locator('#suite-run').click()
        page.wait_for_function("document.getElementById('suite-state').textContent.startsWith('完了')",timeout=10000)
        out=json.loads(page.locator('#suite-output').text_content())
        assert key in out, (route,out)
        assert page.locator('#suite-download').is_visible()
        print('PASS browser:',route,key,out.get(key))
        if route=='kintone-print-report':
            assert page.locator('#suite-print').is_visible()
            assert page.locator('.print-table').is_visible()
            print('PASS print table')
        if route=='kintone-duplicates':
            assert out['duplicateGroups']==1
        if route=='kintone-bulk-preview':
            assert out['writeExecuted'] is False
        assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth+2"),route+' horizontal scroll'
        if route=='kintone-print-report':
            target=Path.home()/'Documents'/'AI-Work'/'ResoArc'/'qa'
            target.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(target/'suite-report-mobile.png'),full_page=True)
    assert not errors, errors
    browser.close()
    print('PASS all 6 browser routes; no JavaScript exceptions')
finally: server.shutdown()
