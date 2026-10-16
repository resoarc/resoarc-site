#!/usr/bin/env python3
"""Kanban: mocked kintone runtime in a real browser, not a real tenant test."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from functools import partial
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'plugins/kanban/v0.1.0-alpha/src/js/desktop.js').read_text(encoding='utf8')
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'site')))
Thread(target=server.serve_forever,daemon=True).start()
ORIGIN='http://127.0.0.1:'+str(server.server_address[1])
cases=[
 ('desktop','/k/42/','/k/42/show#record=8'),
 ('mobile','/k/m/42/','/k/m/42/show?record=8'),
 ('desktop','/k/guest/7/42/','/k/guest/7/42/show#record=8'),
 ('mobile','/k/guest/7/m/42/','/k/guest/7/m/42/show?record=8'),
]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for mode,path,expected in cases:
            page=browser.new_page(viewport={'width':390 if mode=='mobile' else 1200,'height':840})
            page.goto(ORIGIN+'/',wait_until='domcontentloaded')
            page.evaluate("path=>history.replaceState({},'',path)",path)
            page.evaluate("""() => {
              document.body.innerHTML='<main id="mount"></main>';
              const panel=document.getElementById('mount');
              window.apiCalls=[];
              const space={getHeaderSpaceElement:()=>panel,getId:()=>42};
              const api=async(...args)=>{window.apiCalls.push(args);throw Error('unexpected API');};
              window.kintone={$PLUGIN_ID:'mock-kanban',
                plugin:{app:{getConfig:()=>({rules:JSON.stringify([{groupField:'Status',labelField:'Title',limit:20}])})}},
                app:space,mobile:{app:space},api:Object.assign(api,{url:x=>x}),
                events:{on:(k,cb)=>{window.handler=cb;window.registered=k;}}};
            }""")
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.add_script_tag(content=JS)
            assert mode+'.app.record.index.show' in list(page.evaluate('window.registered')) if mode=='mobile' else 'app.record.index.show' in list(page.evaluate('window.registered'))
            data=[
                {'$id':{'value':'8'},'Status':{'value':'Open'},'Title':{'value':'<img src=x onerror=alert(1)>'}},
                {'$id':{'value':'9'},'Status':{'value':'Done'},'Title':{'value':'Approved'}},
            ]
            page.evaluate("({mode,data})=>window.handler({type:mode==='mobile'?'mobile.app.record.index.show':'app.record.index.show',records:data})",{'mode':mode,'data':data})
            assert page.locator('#resoarc-kanban-alpha').count()==1
            link=page.get_by_role('link',name='詳細を開く').first
            assert link.get_attribute('href')==expected,(mode,path,link.get_attribute('href'))
            assert page.locator('#resoarc-kanban-alpha img').count()==0
            assert '<img src=x onerror=alert(1)>' in page.locator('#resoarc-kanban-alpha').inner_text()
            assert page.evaluate('window.apiCalls.length')==0
            assert not errors,(mode,errors)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+8'),(mode,path)
            print('PASS kanban',mode,path,'no writes, safe text, correct link')
            page.close()
        browser.close()
finally:
    server.shutdown()
