#!/usr/bin/env python3
"""Browser integration tests for read-only search and safeguarded grid editor.
Synthetic kintone APIs; this is NOT a real kintone tenant integration test.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def bundle(slug):
 return (ROOT/'plugins'/slug/'v0.1.0-alpha'/'src/js/desktop.js').read_text(encoding='utf-8')
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 for mobile in (False,True):
  page=browser.new_page(viewport={'width':390,'height':844} if mobile else {'width':1280,'height':850})
  page.set_content('<main id="mount"></main>')
  page.evaluate("""({mobile})=>{
   const mount=document.getElementById('mount');
   window.apis=[];
   const api={getHeaderSpaceElement:()=>mount,getQueryCondition:()=> 'Status = "A" or Status = "B"',getId:()=>42};
   const get=async(url,method,body)=>{
    if(method!=='GET')throw Error('unexpected write');
    window.apis.push({url,method,body});
    const last=/\\$id > (\\d+)/.exec(body.query);
    const start=last?Number(last[1]):0;
    const count=start===0?500:1;
    return {records:Array.from({length:count},(_,i)=>({$id:{value:String(start+i+1)},Name:{value:i===0&&start>0?'target':'other'},Status:{value:'A'}}))};
   };
   window.kintone={$PLUGIN_ID:'plugin1',plugin:{app:{getConfig:()=>({rules:JSON.stringify([{code:'Name',label:'Name',operator:'contains'}])})}},
     app:api,mobile:{app:api},api:Object.assign(get,{url:path=>path}),
     events:{on:(names,cb)=>{window.kintoneEvent=cb;window.kintoneEvents=names;}}};
  }""",{'mobile':mobile})
  page.add_script_tag(content=bundle('list-search'))
  event_type='mobile.app.record.index.show' if mobile else 'app.record.index.show'
  page.evaluate("""type=>window.kintoneEvent({type,viewType:'list',records:[{$id:{value:'44'},Name:{value:'on-page'}}]})""",event_type)
  assert page.locator('#resoarc-search-alpha').count()==1
  page.locator('[aria-label="検索語"]').fill('target')
  page.get_by_role('button',name='検索',exact=True).click()
  assert page.locator('#resoarc-search-alpha').get_by_text('0 / 1 件',exact=False).count()==1
  assert page.evaluate('window.apis.length')==0
  page.locator('[aria-label="検索範囲"]').select_option('view')
  page.get_by_role('button',name='検索',exact=True).click()
  page.wait_for_function('document.querySelector("#resoarc-search-alpha [role=status]").textContent.includes("検索完了")')
  assert page.locator('#resoarc-search-alpha').get_by_text('1 / 501 件',exact=False).count()==1
  results=page.evaluate('window.apis')
  assert len(results)==2
  assert '(Status = "A" or Status = "B")' in results[1]['body']['query']
  assert '($id > 500)' in results[1]['body']['query']
  assert results[1]['body']['fields']==['$id','Name']
  print('PASS search', 'mobile' if mobile else 'desktop','GET-only, 2 pages, filter parentheses, bounded')
  page.close()
 for should_fail in (False,True):
  page=browser.new_page(viewport={'width':1280,'height':850})
  page.set_content('<main id="mount"></main>')
  page.evaluate("""({shouldFail})=>{
   const mount=document.getElementById('mount');
   window.writes=[];
   window.confirm=()=>true;
   const api=async(url,method,body)=>{
    if(method!=='PUT')throw Error('unexpected API call');
    window.writes.push({url,method,body});
    if(shouldFail&&body.id==='2')throw Error('simulated conflict');
    return {revision:'2'};
   };
   window.kintone={$PLUGIN_ID:'plugin2',plugin:{app:{getConfig:()=>({rules:'[{"field":"Amount","limit":30}]'})}},
     app:{getHeaderSpaceElement:()=>mount,getId:()=>42},api:Object.assign(api,{url:p=>p}),
     events:{on:(event,cb)=>{window.kintoneEvent=cb;}}};
  }""",{'shouldFail':should_fail})
  page.add_script_tag(content=bundle('grid-editor'))
  event_records=[
   {'$id':{'value':'1'},'$revision':{'value':'1'},'Amount':{'type':'NUMBER','value':'10'}},
   {'$id':{'value':'2'},'$revision':{'value':'3'},'Amount':{'type':'NUMBER','value':'20'}},
   {'$id':{'value':'3'},'$revision':{'value':'2'},'Amount':{'type':'DATE','value':'2026-10-16'}}]
  page.evaluate("""records=>window.kintoneEvent({type:'app.record.index.show',viewType:'list',records})""",event_records)
  assert page.locator('#resoarc-grid-alpha input').count()==2
  assert page.get_by_text('1件のレコードは対象外',exact=False).count()==1
  page.locator('#resoarc-grid-alpha input').first.fill('bogus')
  page.get_by_role('button',name='変更をプレビュー').click()
  assert page.get_by_role('button',name='確認して更新').is_disabled()
  assert page.evaluate('window.writes.length')==0
  page.locator('#resoarc-grid-alpha input').first.fill('11')
  page.locator('#resoarc-grid-alpha input').nth(1).fill('21')
  page.get_by_role('button',name='変更をプレビュー').click()
  page.get_by_role('button',name='確認して更新').click()
  expected='途中停止' if should_fail else '完了'
  page.wait_for_function("""expected=>document.querySelector('#resoarc-grid-alpha [role=status]').textContent.includes(expected)""",arg=expected)
  assert page.evaluate('window.writes.length')==2
  assert page.evaluate('window.writes[0].body.revision')=='1'
  assert page.evaluate('window.writes[1].body.revision')=='3'
  assert page.get_by_role('button',name='確認して更新').is_disabled()
  assert page.get_by_role('button',name='変更をプレビュー').is_disabled()
  print('PASS grid', 'partial failure' if should_fail else 'success','type-block, confirmed PUT, revision, no re-submit')
  page.close()
 browser.close()
print('BROWSER_RUNTIME_PASS')
