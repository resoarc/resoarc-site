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
            existing=SITE/'assets/qaiuick-spec'/f'current-{slug}.json'
            baseline=SITE/'assets/qaiuick-spec'/f'baseline-{slug}.json'
            with tempfile.TemporaryDirectory() as td:
                fresh=pathlib.Path(td)/'fresh.json'
                args=['node',str(cli),'snapshot',str(SITE/'assets/qaiuick-spec'/f'{slug}.spec.js'),str(fresh)]
                result=subprocess.run(args,capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(fresh.read_text('utf8')),json.loads(existing.read_text('utf8')))
                self.assertNotEqual(existing.read_text('utf8'),baseline.read_text('utf8'))
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
                self.assertIn('IMPACT',result.stdout)
                impact=subprocess.run(['node',str(cli),'diff',str(baseline),str(existing)],
                    capture_output=True,text=True,timeout=15)
                self.assertEqual(impact.returncode,0,impact.stderr)
                self.assertIn('DATA_REVIEW_REQUIRED',impact.stdout)
                self.assertIn('フォーム配置',impact.stdout)

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


    def test_field_contract_and_section_validation_are_pure(self):
        snippet = r"""
import { normalizeSpec, validateRecord, impactReport } from './site/assets/qaiuick/spec.js';
const spec={
  id:'stock-check',version:2,title:'Stock',
  fields:{
    name:{label:'Name',required:true,unique:true,minLength:2},
    qty:{label:'Qty',type:'number',integer:true,min:0},
  },
  ui:{sections:[{title:'Main',fields:['name','qty']}],detail:['name']},
};
const s=normalizeSpec(spec);
const old=[{id:'one',name:'ABC',qty:4}];
const mustReject=(draft,editing='') => {
  let ok=false;
  try {validateRecord(s,draft,old,editing);} catch (_) {ok=true;}
  if (!ok) throw new Error('Validation unexpectedly passed');
};
mustReject({name:'abc',qty:1}); // case-insensitive unique
mustReject({name:'DEF',qty:1.5}); // integer
mustReject({name:'D',qty:1}); // minLength
const good=validateRecord(s,{name:'ABC',qty:'8'},old,'one');
if(good.qty!==8)throw new Error('Edit validation failed');
let rejected=false;
try{ normalizeSpec({...spec,ui:{sections:[{title:'Missing',fields:['name']}]}}); }
catch(_){rejected=true;}
if(!rejected)throw new Error('Missing form field was accepted');
console.log('SPEC_VALIDATION_PASS');
"""
        result=subprocess.run(['node','--input-type=module','-e',snippet],cwd=ROOT,
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('SPEC_VALIDATION_PASS',result.stdout)


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
                self.assertTrue(z.read(prefix+'src/'+f).startswith(b'/*'),
                                'Older distributable must retain its frozen source')
            self.assertIn(b'../src/spec.js', z.read(prefix+'tools/qaiuick_spec.mjs'))
            self.assertIn(b'fields:', z.read(prefix+'examples/spec-inventory/spec.js'))


    def test_v05_archive_contains_latest_spec_and_impact_tool(self):
        from zipfile import ZipFile
        import hashlib
        path=SITE/'downloads/qaiuick-v0.5-beta-source.zip'
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(path.with_suffix('.zip.sha256').read_text('ascii').strip(),
                         f'{digest}  {path.name}')
        prefix='qAIUIck-v0.5-beta/'
        with ZipFile(path) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(len(z.namelist()),45)
            self.assertEqual(json.loads(z.read(prefix+'package.json'))['version'],'0.5.0')
            for f in ('spec.js','define.js','define.css'):
                self.assertTrue(z.read(prefix+'src/'+f).startswith(b'/*'),
                                'Frozen v0.5 distribution must remain intact')
            self.assertIn(b'IMPACT',z.read(prefix+'tools/qaiuick_spec.mjs'))
            for slug in ('inventory','tickets'):
                self.assertEqual(
                    json.loads(z.read(prefix+f'examples/spec-{slug}/current.json')),
                    json.loads((SITE/'assets/qaiuick-spec'/f'current-{slug}.json').read_text('utf8'))
                )
                self.assertIn(b'ui:',z.read(prefix+f'examples/spec-{slug}/spec.js'))

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
            page.wait_for_function('() => document.querySelector(".qs-diff").textContent.includes("fields.name.unique")')
            self.assertIn('保存済みレコード', page.locator('.qs-impact').inner_text())
            self.assertIn('"fields"',page.locator('.qs-inspector .qs-code').first.inner_text())
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth - window.innerWidth'),2)
        finally:page.close()

    def test_extension_slots_follow_requested_section_order(self):
        page=self.open('inventory')
        try:
            order=page.evaluate("""async () => {
              const { defineApp } = await import('/assets/qaiuick/define.js');
              const root=document.createElement('section');
              root.id='slot-test';
              document.body.append(root);
              defineApp({
                id:'slot-test-2026', version:1, title:'Slots',
                root:'#slot-test', persist:'memory',
                fields:{ title:'Item*' },
                slots:{
                  beforeForm:({node})=>node('div',{'data-slot':'before'},'Custom before form'),
                  afterList:({node})=>node('div',{'data-slot':'after'},'Custom after list'),
                },
              });
              return [...root.children].map(el => el.dataset.slot ||
                (el.classList.contains('qs-inspector') ? 'inspector' :
                 el.classList.contains('qs-panel') && el.querySelector('form') ? 'form' :
                 el.classList.contains('qs-panel') ? 'list' : 'other'));
            }""")
            self.assertEqual(order,['other','other','before','form','list','after','inspector'])
        finally:
            page.close()


    def test_declarative_layout_detail_and_validation(self):
        page=self.open('inventory')
        try:
            self.assertEqual(page.locator('.qs-form-section').count(),2)
            self.assertEqual(page.locator('.qs-form-section legend').all_inner_texts(),
                             ['品目情報','在庫と補充'])
            page.locator('button[q-action="view"]').nth(1).click()
            self.assertTrue(page.locator('.qs-detail').is_visible())
            self.assertIn('USB-Cケーブル',page.locator('.qs-detail').inner_text())
            page.locator('button[q-action="closeDetail"]').click()
            self.assertFalse(page.locator('.qs-detail').is_visible())
            page.locator('input[q-model="draft.name"]').fill('M3ボルト')
            page.locator('form[q-submit="save"] button[type="submit"]').click()
            self.assertEqual(page.locator('.qs-table tbody tr').count(),3)
            self.assertIn('既に登録', page.locator('p.q-error').inner_text())
            page.locator('input[q-model="draft.name"]').fill('M8ボルト')
            page.locator('input[q-model="draft.qty"]').fill('1.5')
            page.locator('form[q-submit="save"] button[type="submit"]').click()
            self.assertEqual(page.locator('.qs-table tbody tr').count(),3)
            page.locator('input[q-model="draft.qty"]').fill('7')
            page.locator('form[q-submit="save"] button[type="submit"]').click()
            self.assertEqual(page.locator('.qs-table tbody tr').count(),4)
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth-window.innerWidth'),2)
        finally:
            page.close()

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
