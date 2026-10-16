#!/usr/bin/env python3
"""Replace JSON-only kintone alpha config with schema-checked accessible field forms."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
specs={
 'conditional-format':{'core':'ResoArcFormatting','min':1,'max':30,'fields':[
  {'key':'source','label':'判定元フィールドコード','kind':'field'},
  {'key':'target','label':'装飾するフィールドコード','kind':'field'},
  {'key':'operator','label':'判定条件','kind':'select','options':[['eq','一致'],['neq','不一致'],['includes','含む'],['empty','空欄'],['not_empty','空欄でない'],['gt','より大きい'],['gte','以上'],['lt','より小さい'],['lte','以下']]},
  {'key':'value','label':'比較値（空欄判定では不要）','kind':'text'},
  {'key':'theme','label':'配色','kind':'select','options':[['navy','紺'],['amber','琥珀'],['red','赤'],['green','緑'],['gray','灰']]}],
 'defaults':{'source':'','target':'','operator':'eq','value':'','theme':'amber'}},
 'date-calculator':{'core':'ResoArcDates','min':1,'max':30,'fields':[
  {'key':'start','label':'開始日フィールドコード（DATE）','kind':'field'},
  {'key':'end','label':'終了日フィールドコード（DATE）','kind':'field'},
  {'key':'target','label':'出力先フィールドコード（数値・文字列）','kind':'field'},
  {'key':'mode','label':'日数の計算方法','kind':'select','options':[['calendar','暦日'],['business','営業日（土日除外）']]},
  {'key':'holidays','label':'追加で除外する祝日 YYYY-MM-DD（改行かカンマで区切る）','kind':'dates'}],
 'defaults':{'start':'','end':'','target':'','mode':'calendar','holidays':[]}},
 'list-search':{'core':'ResoArcListSearch','min':1,'max':8,'fields':[
  {'key':'code','label':'検索するフィールドコード','kind':'field'},
  {'key':'label','label':'検索項目の表示名','kind':'text'},
  {'key':'operator','label':'一致方式','kind':'select','options':[['contains','含む'],['equals','完全一致'],['startsWith','前方一致']]}],
 'defaults':{'code':'','label':'','operator':'contains'}},
 'grid-editor':{'core':'ResoArcGrid','min':1,'max':1,'fields':[
  {'key':'field','label':'編集するフィールドコード（文字列・数値のみ）','kind':'field'},
  {'key':'limit','label':'一覧に表示する最大行数（1〜100）','kind':'number','min':1,'max':100}],
 'defaults':{'field':'','limit':30}},
 'kanban':{'core':'ResoArcKanban','min':1,'max':1,'fields':[
  {'key':'groupField','label':'列分けするフィールドコード','kind':'field'},
  {'key':'labelField','label':'カード見出しのフィールドコード','kind':'field'},
  {'key':'limit','label':'一覧に表示する最大件数（1〜100）','kind':'number','min':1,'max':100}],
 'defaults':{'groupField':'','labelField':'','limit':60}}
}
common_js=r"""/* ResoArc field-based settings UI / MIT */
(function(pid){
'use strict';
const spec=__SPEC__;
const core=globalThis[spec.core], root=document.getElementById('rule-list');
const alert=document.getElementById('error'), note=document.getElementById('note');
const cfg=kintone.plugin.app.getConfig(pid)||{};
const defaultRule=()=>JSON.parse(JSON.stringify(spec.defaults));
function button(label,callback){
 const b=document.createElement('button');b.type='button';b.textContent=label;b.addEventListener('click',callback);return b;
}
function text(parent,tag,value){
 const item=document.createElement(tag);item.textContent=value;parent.appendChild(item);return item;
}
let initial;
try{
 const raw=cfg.rules?JSON.parse(cfg.rules):null;
 initial=raw&&core&&core.normalize(raw)?raw:null;
}catch(_){initial=null;}
if(cfg.rules&&!initial){alert.textContent='保存済み設定が不正です。修正してから保存してください。';}
let rows=initial||[defaultRule()];
const inputId='ra-fields-'+pid.replace(/[^A-Za-z0-9_-]/g,'');
const fieldList=document.createElement('datalist');fieldList.id=inputId;document.body.appendChild(fieldList);
const allowedTypes={
 ResoArcDates:{start:['DATE'],end:['DATE'],target:['NUMBER','SINGLE_LINE_TEXT','MULTI_LINE_TEXT']},
 ResoArcGrid:{field:['SINGLE_LINE_TEXT','MULTI_LINE_TEXT','NUMBER']}
};
let fieldMetadata=null;
function checkFields(candidate){
 if(!fieldMetadata||typeof fieldMetadata!=='object')throw Error('フォームの項目情報を取得できません。アクセス権とネットワークを確認してから再試行してください。');
 const policy=allowedTypes[spec.core]||{};
 for(const rule of candidate){
  for(const field of spec.fields.filter(f=>f.kind==='field')){
   const code=rule[field.key];
   const info=fieldMetadata[code];
   if(!info||!info.type||['SUBTABLE','REFERENCE_TABLE','GROUP','SPACER','LABEL','HR'].includes(info.type))throw Error('フィールド「'+code+'」が見つからないか、このプラグインでは使えません。');
   if(policy[field.key]&&!policy[field.key].includes(info.type))throw Error('フィールド「'+code+'」の型 '+info.type+' は対象外です。');
  }
 }
}
async function loadFields(){
 const app=kintone.app;
 let properties;
 if(app&&typeof app.getFormFields==='function')properties=await app.getFormFields();
 else {
  const id=app&&app.getId&&app.getId();
  if(!id||typeof kintone.api!=='function')throw Error('フィールド情報の取得APIが使えません');
  const data=await kintone.api(kintone.api.url('/k/v1/app/form/fields.json',true),'GET',{app:id});
  properties=data&&data.properties;
 }
 if(!properties||typeof properties!=='object')throw Error('フィールド情報が空です');
 fieldMetadata=properties;
 for(const [code,info] of Object.entries(properties)){
  if(typeof code!=='string'||code.length>128)continue;
  const opt=document.createElement('option');opt.value=code;opt.textContent=String(info.label||code)+' ('+String(info.type||'')+')';fieldList.appendChild(opt);
 }
 return properties;
}
const fieldPromise=loadFields().catch(err=>{fieldMetadata=null;note.textContent='フィールド情報の取得に失敗しました。設定保存には取得権限が必要です。';return null;});
function readRows(){
 return [...root.querySelectorAll('[data-rule]')].map(group=>{
  const row={};
  for(const field of spec.fields){
   const element=group.querySelector('[data-field="'+field.key+'"]');
   const raw=element.value.trim();
   if(field.kind==='dates')row[field.key]=raw?raw.split(/[\s,;]+/).filter(Boolean):[];
   else if(field.kind==='number')row[field.key]=raw===''?null:Number(raw);
   else row[field.key]=raw;
  }
  return row;
 });
}
function render(){
 root.replaceChildren();
 rows.forEach((record,i)=>{
  const section=document.createElement('fieldset');section.dataset.rule=String(i);root.appendChild(section);
  text(section,'legend','ルール '+(i+1));
  for(const field of spec.fields){
   const label=document.createElement('label');label.className='ra-control';section.appendChild(label);
   text(label,'span',field.label);
   let input;
   if(field.kind==='select'){
    input=document.createElement('select');
    for(const [value,title] of field.options){
     const option=document.createElement('option');option.value=value;option.textContent=title;input.appendChild(option);
    }
   }else if(field.kind==='dates'){
    input=document.createElement('textarea');input.rows=3;input.placeholder='2026-01-01, 2026-01-02';
   }else{
    input=document.createElement('input');input.type=field.kind==='number'?'number':'text';
    if(field.kind==='field'){input.setAttribute('list',inputId);input.maxLength=128;}
    if(field.kind==='text')input.maxLength=200;
    if(field.kind==='number'){input.min=String(field.min);input.max=String(field.max);input.step='1';}
    if(field.kind==='field')input.placeholder='例: '+field.key+'_field';
   }
   input.dataset.field=field.key;
   const value=record[field.key];
   input.value=Array.isArray(value)?value.join('\n'):value==null?'':String(value);
   label.appendChild(input);
  }
  if(spec.max>1)section.appendChild(button('このルールを削除',()=>{
    rows=readRows();rows.splice(i,1);
    if(rows.length===0)rows.push(defaultRule());
    alert.textContent='';render();
  }));
 });
 const add=document.getElementById('add');add.hidden=spec.max===1||rows.length>=spec.max;
 note.textContent='設定できるルール: '+rows.length+' / '+spec.max+'件。フィールドコードはアプリの設定画面で確認できます。';
}
document.getElementById('add').addEventListener('click',()=>{
 rows=readRows();if(rows.length>=spec.max)return;
 rows.push(defaultRule());alert.textContent='';render();
});
document.getElementById('save').addEventListener('click',async()=>{
 alert.textContent='';
 try{
  const candidate=readRows();
  if(candidate.length<spec.min||candidate.length>spec.max||!core||!core.normalize(candidate)){
   throw Error('設定値が正しくありません。フィールドコード・重複・数値・日付を確認してください。');
  }
  await fieldPromise;
  checkFields(candidate);
  kintone.plugin.app.setConfig({rules:JSON.stringify(candidate)});
  note.textContent='設定を保存しました。アプリの設定を更新して適用してください。';
 }catch(e){alert.textContent=e.message||String(e);}
});
document.getElementById('cancel').addEventListener('click',()=>history.back());
render();
// kintone.app.getFormFields() is supported on plugin configuration pages.
// Field metadata must be available before a configuration can be saved.
})(kintone.$PLUGIN_ID);
"""
html='''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body><main class="ra-rule-config">
<h1>__NAME__</h1>
<p>フィールドコードを指定してルールを作成します。実際のレコードを変更する前にテストアプリで検証してください。</p>
<div id="rule-list"></div>
<div class="ra-actions"><button type="button" id="add">＋ ルールを追加</button><button type="button" id="save">設定を保存</button><button type="button" id="cancel">戻る</button></div>
<p role="alert" id="error"></p><p role="status" id="note"></p></main></body></html>
'''
css='''*{box-sizing:border-box}body{font-family:system-ui,sans-serif;color:#1e2c3d;background:#f4f6f8;padding:12px}main{max-width:840px;margin:auto;background:#fff;border:1px solid #d2dce5;border-radius:10px;padding:18px}fieldset{border:1px solid #bccbd9;border-radius:8px;margin:16px 0;padding:14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}legend{font-weight:700}.ra-control{display:flex;flex-direction:column;gap:5px}.ra-control span{font-weight:600}.ra-control input,.ra-control select,.ra-control textarea{font:inherit;min-height:40px;width:100%;padding:8px;border:1px solid #8498ac;border-radius:5px}.ra-actions{display:flex;flex-wrap:wrap;gap:8px}button{font:inherit;padding:10px 14px;background:#f2f6fa;border:1px solid #8fa7bc;border-radius:6px;cursor:pointer}button#save{color:#fff;background:#215e9f}button:hover{filter:brightness(.95)}#error{color:#9b1c1c;font-weight:700}#note{color:#385168}'''
for slug,spec in specs.items():
 root=ROOT/'plugins'/slug/'v0.1.0-alpha'
 manifest_file=root/'src/manifest.json'
 manifest=json.loads(manifest_file.read_text(encoding='utf-8-sig'))
 manifest['config']['js']=['js/core.js','js/config.js']
 manifest_file.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 (root/'src/js/config.js').write_text(common_js.replace('__SPEC__',json.dumps(spec,ensure_ascii=False,separators=(',',':'))).rstrip('\n')+'\n',encoding='utf-8',newline='\n')
 name=manifest['name']['ja']
 (root/'src/html/config.html').write_text(html.replace('__NAME__',name),encoding='utf-8',newline='\n')
 (root/'src/css/config.css').write_text(css+'\n',encoding='utf-8',newline='\n')
 print('IMPROVED',slug)
