from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'site'
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
thread=Thread(target=server.serve_forever,daemon=True);thread.start()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for width in [390,1280]:
            page=browser.new_page(viewport={'width':width,'height':844})
            response=page.goto('http://127.0.0.1:'+str(server.server_address[1])+'/os/pi/',wait_until='domcontentloaded')
            assert response.status==200
            assert page.title().startswith('ResoArcOS Raspberry Pi')
            assert page.get_by_text('IMG未配布').count()>=1
            assert page.locator('a[href="/downloads/resoarcos-pi-firstboot-v0.2.1-alpha-source.zip"]').count()==1
            layout=page.evaluate('({scroll:document.documentElement.scrollWidth,width:innerWidth})')
            assert layout['scroll']<=layout['width']+6,layout
            resp=page.request.get('http://127.0.0.1:'+str(server.server_address[1])+'/downloads/resoarcos-pi-firstboot-v0.2.1-alpha-source.zip')
            assert resp.status==200 and len(resp.body())>25000
            print('PASS Pi site',width,'ZIP',len(resp.body()),'layout',layout)
            page.close()
        page=browser.new_page()
        response=page.goto('http://127.0.0.1:'+str(server.server_address[1])+'/os/')
        assert response.status==200
        assert page.locator('a[href="/os/pi/"]').count()==1
        print('PASS PC->Pi navigation')
        browser.close()
finally:
    server.shutdown()
