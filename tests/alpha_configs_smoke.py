#!/usr/bin/env python3
"""Browser smoke test for five kintone alpha configuration panels."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
CASES={
'conditional-format':({'source':'risk','target':'amount','operator':'gte','value':'80','theme':'red'},'target'),
'date-calculator':({'start':'start_date','end':'end_date','target':'duration','mode':'business','holidays':'2026-01-01,2026-01-02'},'target'),
'list-search':({'code':'Name','label':'名前','operator':'contains'},'code'),
'grid-editor':({'field':'Notes','limit':'20'},'field'),
'kanban':({'groupField':'Status','labelField':'Title','limit':'60'},'groupField')
}
base='plugins'
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 for slug,(inputs,unique) in CASES.items():
  root=ROOT/base/slug/'v0.1.0-alpha/src'
  page=browser.new_page(viewport={'width':390,'height':844})
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content((root/'html/config.html').read_text(encoding='utf-8'))
  page.evaluate("""() => {
    window.saved=null;
    const properties={
      risk:{type:'NUMBER'},amount:{type:'NUMBER'},
      start_date:{type:'DATE'},end_date:{type:'DATE'},duration:{type:'NUMBER'},
      Name:{type:'SINGLE_LINE_TEXT'},Notes:{type:'SINGLE_LINE_TEXT'},
      Status:{type:'DROP_DOWN'},Title:{type:'SINGLE_LINE_TEXT'}
    };
    window.kintone={$PLUGIN_ID:'test',plugin:{app:{getConfig:()=>({}),setConfig:cfg=>{window.saved=cfg;}}},
       app:{getId:()=>1,getFormFields:async()=>properties},
       api:Object.assign(async()=>({properties}),{url:url=>url})};
  }""")
  page.add_script_tag(content=(root/'js/core.js').read_text(encoding='utf-8'))
  page.add_script_tag(content=(root/'js/config.js').read_text(encoding='utf-8'))
  assert page.locator('fieldset').count()==1,(slug,'initial rule')
  page.locator('#save').click()
  assert page.locator('#error').inner_text(),(slug,'should reject blank rule')
  for key,value in inputs.items():
   page.locator(f'[data-field="{key}"]').first.fill(value) if key not in ('mode','operator','theme') else page.locator(f'[data-field="{key}"]').first.select_option(value)
  page.locator('#save').click()
  assert not page.locator('#error').inner_text(),(slug,page.locator('#error').inner_text())
  result=page.evaluate("JSON.parse(window.saved.rules)")
  assert len(result)==1 and result[0][unique]==inputs[unique],(slug,result)
  if slug=='date-calculator':
   assert result[0]['holidays']==['2026-01-01','2026-01-02']
  target=page.locator(f'[data-field="{unique}"]').first
  target.fill('missing_field_code')
  page.locator('#save').click()
  assert '見つからない' in page.locator('#error').inner_text(),(slug,'missing code must be rejected')
  target.fill(inputs[unique])
  if slug=='date-calculator':
   page.locator('[data-field="start"]').first.fill('Title')
   page.locator('#save').click()
   assert '型' in page.locator('#error').inner_text(),(slug,'DATE type validation')
   page.locator('[data-field="start"]').first.fill('start_date')
  if slug=='grid-editor':
   target.fill('start_date')
   page.locator('#save').click()
   assert '型' in page.locator('#error').inner_text(),(slug,'grid type validation')
   target.fill(inputs[unique])
  page.locator('#save').click()
  assert not page.locator('#error').inner_text(),(slug,'restoring valid settings should save')
  if slug in ['date-calculator','conditional-format','list-search']:
   page.locator('#add').click()
   assert page.locator('fieldset').count()==2
   for key,value in inputs.items():
    target=page.locator(f'[data-field="{key}"]').nth(1)
    target.select_option(value) if key in ('mode','operator','theme') else target.fill(value)
   page.locator('#save').click()
   assert page.locator('#error').inner_text(),(slug,'duplicate rule should fail')
   page.get_by_text('このルールを削除').last.click()
   assert page.locator('fieldset').count()==1
  assert not errors,(slug,errors)
  page.close()
  print('PASS',slug,'form-save validation, constraints, mobile viewport, page errors 0')
 browser.close()
