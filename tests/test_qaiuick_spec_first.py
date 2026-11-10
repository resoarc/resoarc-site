# SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
# SPDX-License-Identifier: MIT
"""Spec-first qAIUIck: DOM behavior, schema changes and local persistence."""
from __future__ import annotations
import functools
import http.server
import json
import pathlib
import shutil
import subprocess
import tempfile
import threading
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

@unittest.skipUnless(shutil.which('node'), 'Node.js missing')
class SpecCLITest(unittest.TestCase):
    def test_snapshots_match_source_and_diff_tracks_field_and_behavior(self):
        cli=ROOT/'tools/qaiuick_spec.mjs'
        for slug in ('inventory','tickets'):
            existing=SITE/'assets/qaiuick-spec'/f'baseline-{slug}.json'
            with tempfile.TemporaryDirectory() as td:
                fresh=pathlib.Path(td)/'fresh.json'
                args=['node',str(cli),'snapshot',str(SITE/'assets/qaiuick-spec'/f'{slug}.spec.js'),str(fresh)]
                result=subprocess.run(args,capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(fresh.read_text('utf8')),json.loads(existing.read_text('utf8')))
                before=json.loads(existing.read_text('utf8'))
                after=json.loads(existing.read_text('utf8'))
                after['fields'][next(iter(after['fields']))]['required']=not after['fields'][next(iter(after['fields']))]['required']
                for action in after['actions'].values():
                    action['logic']+=' // changed by AI'
                    break
                changed=pathlib.Path(td)/'changed.json'
                changed.write_text(json.dumps(after),encoding='utf-8')
                result=subprocess.run(['node',str(cli),'diff',str(existing),str(changed)],capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('fields.',result.stdout)
                self.assertIn('.logic',result.stdout)

    def test_malicious_fields_and_unknown_types_are_rejected(self):
        snippet="""
import { normalizeSpec } from './site/assets/qaiuick/spec.js';
const prototype={id:'safe-app',version:1,title:'Safe',fields:{__proto__:{label:'evil'}}};
for(const fields of [{ dangerous:{type:'html',label:'no'} }, {'constructor':'unsafe'}]) {
  let failed=false;
  try {normalizeSpec({...prototype,fields});} catch(_) {failed=true;}
  if(!failed) process.exit(2);
}
console.log('SPEC_REJECTION_PASS');
"""
        run=subprocess.run(['node','--input-type=module','-e',snippet],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr)


class SpecDistributionTest(unittest.TestCase):
    def test_v04_archive_integrity_and_single_source(self):
        from zipfile import ZipFile
        import hashlib
        path=SITE/'downloads/qaiuick-v0.4-beta-source.zip'
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        check=path.with_suffix('.zip.sha256').read_text('ascii').strip()
        self.assertEqual(check, f'{digest}  {path.name}')
        prefix='qAIUIck-v0.4-beta/'
        with ZipFile(path) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(json.loads(z.read(prefix+'package.json'))['version'],'0.4.0')
            for f in ('spec.js','define.js','define.css'):
                self.assertEqual(z.read(prefix+'src/'+f),(SITE/'assets/qaiuick'/f).read_bytes())
            self.assertIn(b'../src/spec.js', z.read(prefix+'tools/qaiuick_spec.mjs'))
            self.assertIn(b'fields:', z.read(prefix+'examples/spec-inventory/spec.js'))

@unittest.skipUnless(sync_playwright,'Playwright missing')
class SpecBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler=functools.partial(QuietHandler,directory=str(SITE))
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def open(self,slug):
        page=self.browser.new_page(viewport={'width':390,'height':844})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        r=page.goto(self.base+'/tools/qaiuick-spec-'+slug+'/',wait_until='networkidle')
        self.assertEqual(r.status,200)
        page.wait_for_function('() => document.querySelectorAll(".qs-table tbody tr").length === 3')
        self.assertFalse(errors,errors)
        return page

    def test_inventory_crud_search_snapshot_and_safety(self):
        page=self.open('inventory')
        try:
            self.assertEqual(page.locator('[q-text="low"]').inner_text(),'1')
            page.locator('input[q-model="query"]').fill('ケーブル')
            self.assertEqual(page.locator('.qs-table tbody tr').count(),1)
            page.locator('input[q-model="query"]').fill('')
            page.locator('button[q-action="restock"]').nth(1).click()
            self.assertEqual(page.locator('.qs-table tbody tr').nth(1).locator('td').nth(2).inner_text(),'18')
            page.locator('button[q-action="edit"]').first.click()
            page.locator('input[q-model="draft.name"]').fill('M4ボルト')
            page.locator('button[q-submit="save"]').count() # form has attribute, button does not
            page.locator('form[q-submit="save"] button[type="submit"]').click()
            self.assertIn('M4ボルト',page.locator('.qs-table tbody tr').first.inner_text())
            page.reload(wait_until='networkidle')
            self.assertIn('M4ボルト',page.locator('.qs-table tbody tr').first.inner_text())
            page.locator('input[q-model="draft.name"]').fill('<script>alert(1)</script>')
            page.locator('form[q-submit="save"] button[type="submit"]').click()
            self.assertEqual(page.locator('.qs-table tbody tr script').count(),0)
            page.locator('details.qs-inspector').evaluate('(el)=>el.open=true')
            page.wait_for_function('() => document.querySelector(".qs-diff").textContent.includes("変更はありません")')
            self.assertIn('"fields"',page.locator('.qs-inspector .qs-code').first.inner_text())
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth - window.innerWidth'),2)
        finally:page.close()

    def test_tickets_workflow_delete_reset(self):
        page=self.open('tickets')
        try:
            page.locator('button[q-action="advance"]').first.click()
            self.assertIn('対応中',page.locator('.qs-table tbody tr').first.inner_text())
            page.locator('button[q-action="remove"]').first.click()
            self.assertEqual(page.locator('.qs-table tbody tr').count(),2)
            page.locator('button[q-action="reset"]').click()
            self.assertEqual(page.locator('.qs-table tbody tr').count(),3)
            page.locator('input[q-model="draft.title"]').fill('追加テスト')
            page.locator('input[q-model="draft.owner"]').fill('佐藤')
            page.locator('form[q-submit="save"] button[type="submit"]').click()
            self.assertEqual(page.locator('.qs-table tbody tr').count(),4)
        finally:page.close()

if __name__=='__main__':unittest.main()
