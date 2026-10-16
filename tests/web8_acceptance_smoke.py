#!/usr/bin/env python3
"""Acceptance regression: the two older browser-only tools.
Test real user file upload, malformed data, HTML escaping, and network privacy.
"""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'site'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_address[1])
try:
 with sync_playwright() as playwright:
  browser=playwright.chromium.launch(headless=True)
  for width in (390,1280):
   page=browser.new_page(viewport={'width':width,'height':844},accept_downloads=True)
   external=[]
   errors=[]
   page.on('request',lambda request:external.append(request.url) if not request.url.startswith(url) else None)
   page.on('pageerror',lambda err:errors.append(str(err)))
   response=page.goto(url+'/tools/kintone-app-diff/',wait_until='domcontentloaded')
   assert response.status==200
   page.locator('#diff-before').set_input_files({'name':'before.json','mimeType':'application/json','buffer':b'{"fields":{"A":{"label":"Old"}},"api_token":"old-secret-value"}'})
   page.locator('#diff-after').set_input_files({'name':'after.json','mimeType':'application/json','buffer':b'{"fields":{"A":{"label":"New"}},"api_token":"new-secret-value"}'})
   page.locator('#diff-run').click()
   page.wait_for_function("document.querySelector('#diff-status').textContent.includes('比較完了')")
   assert '変更 2件' in page.locator('#diff-summary').inner_text(),page.locator('#diff-summary').inner_text()
   assert '[MASKED]' in page.locator('#diff-body').inner_text()
   assert 'new-secret-value' not in page.locator('#diff-body').inner_text()
   page.locator('#diff-before').set_input_files({'name':'empty.json','mimeType':'application/json','buffer':b'{}'})
   page.locator('#diff-after').set_input_files({'name':'secret.json','mimeType':'application/json','buffer':b'{"nested":{"secret_key":"DO-NOT-DISPLAY-THIS","api_token":"hidden"}}'})
   page.locator('#diff-run').click()
   page.wait_for_function("document.querySelector('#diff-status').textContent.includes('比較完了')")
   assert 'DO-NOT-DISPLAY-THIS' not in page.locator('#diff-body').inner_text()
   assert '[MASKED]' in page.locator('#diff-body').inner_text()
   page.locator('#diff-before').set_input_files({'name':'broken.json','mimeType':'application/json','buffer':b'{"broken":'})
   page.locator('#diff-run').click()
   page.wait_for_function("document.querySelector('#diff-status').textContent.includes('比較できませんでした')")
   assert page.locator('#diff-result').is_hidden()
   response=page.goto(url+'/tools/kintone-import-check/',wait_until='domcontentloaded')
   assert response.status==200
   schema=b'{"properties":{"name":{"code":"name","label":"Name","type":"SINGLE_LINE_TEXT","required":true},"amount":{"code":"amount","label":"Amount","type":"NUMBER","required":true}}}'
   csv=b'name,amount\nAlice,200\n<img src=x onerror=alert(1)>,abc\n'
   page.locator('#import-form').set_input_files({'name':'form.json','mimeType':'application/json','buffer':schema})
   page.locator('#import-csv').set_input_files({'name':'input.csv','mimeType':'text/csv','buffer':csv})
   page.locator('#import-run').click()
   page.wait_for_function("document.querySelector('#import-status').textContent.includes('検査完了')")
   assert page.locator('#import-result').is_visible()
   assert '数値形式' in page.locator('#import-issues').inner_text()
   assert page.locator('#import-issues img').count()==0
   page.locator('#import-csv').set_input_files({'name':'bad.csv','mimeType':'text/csv','buffer':b'name,amount\n"unclosed\n'})
   page.locator('#import-run').click()
   page.wait_for_function("document.querySelector('#import-status').textContent.includes('検査できませんでした')")
   assert page.locator('#import-result').is_hidden()
   assert not errors,(width,errors)
   assert not external,(width,external)
   assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+7'),width
   print('PASS browser v1 acceptance',width,'app diff + import preflight, invalid data, mask, no external requests')
   page.close()
  browser.close()
finally:server.shutdown()
