/* ResoArc Conditional Fields alpha configuration / MIT */
(function(pluginId){
'use strict';
const $=id=>document.getElementById(id),holder=$('ra-rules');
const old=kintone.plugin.app.getConfig(pluginId)||{};
let saved=[];try{saved=JSON.parse(old.rules||'[]');if(!Array.isArray(saved))saved=[];}catch(_){saved=[];}
let fields=[];
const operations=[['eq','一致'],['neq','不一致'],['includes','部分一致'],['empty','空欄'],['not_empty','空欄でない'],['gt','数値 >'],['gte','数値 ≥'],['lt','数値 <'],['lte','数値 ≤']];
function fieldOptions(select,selected,exclude){
 select.replaceChildren();
 const first=document.createElement('option');first.value='';first.textContent='選択してください';select.append(first);
 for(const f of fields){
  if(exclude.has(f.type))continue;
  const x=document.createElement('option');x.value=f.code;x.textContent=f.label+' ('+f.code+')';select.append(x);
 }
 select.value=selected||'';
}
function ruleLine(data={}){
 if(holder.children.length>=30){$('ra-error').textContent='最大30件です。';return;}
 const root=document.createElement('section');root.className='ra-rule';
 const grid=document.createElement('div');grid.className='ra-grid';
 function field(label,tag,setup){
  const l=document.createElement('label');l.textContent=label;
  const input=document.createElement(tag);setup(input);l.append(input);grid.append(l);return input;
 }
 const source=field('条件元フィールド','select',el=>fieldOptions(el,data.source,new Set(['SUBTABLE','GROUP','LABEL','SPACER','HR','REFERENCE_TABLE','CALC','FILE','RECORD_NUMBER','CREATED_TIME','UPDATED_TIME','CREATOR','MODIFIER','STATUS','STATUS_ASSIGNEE','CATEGORY'])));
 const op=field('条件','select',el=>{for(const [code,label] of operations){const o=document.createElement('option');o.value=code;o.textContent=label;el.append(o);}el.value=data.operator||'eq';});
 const target=field('表示対象','select',el=>fieldOptions(el,data.target,new Set(['SUBTABLE','GROUP','LABEL','SPACER','HR','REFERENCE_TABLE','CALC','RECORD_NUMBER','CREATED_TIME','UPDATED_TIME','CREATOR','MODIFIER','STATUS','STATUS_ASSIGNEE','CATEGORY','FILE'])));
 const value=field('比較する値','input',el=>{el.type='text';el.value=data.value||'';el.maxLength=256;});
 const req=document.createElement('label');req.className='ra-required';req.textContent='条件成立時に入力必須';
 const check=document.createElement('input');check.type='checkbox';check.checked=!!data.required;req.prepend(check);
 const remove=document.createElement('button');remove.type='button';remove.textContent='このルールを削除';remove.className='ra-secondary ra-remove';
 remove.addEventListener('click',()=>root.remove());
 const toggle=()=>{value.disabled=['empty','not_empty'].includes(op.value);};
 op.addEventListener('change',toggle);toggle();
 root.append(grid,req,remove);holder.append(root);
 return {root,source,op,target,value,check};
}
function readRules(){
 const list=[],targets=new Set();
 for(const root of holder.querySelectorAll('.ra-rule')){
  const selects=root.querySelectorAll('select');
  const source=selects[0].value,operator=selects[1].value,target=selects[2].value;
  const value=root.querySelector('input[type=text]').value.trim();
  const required=root.querySelector('input[type=checkbox]').checked;
  if(!source||!target||source===target)throw Error('条件元と表示対象のフィールドを正しく選択してください。');
  if(targets.has(target))throw Error('同じ表示対象フィールドは複数ルールに使えません。');
  targets.add(target);list.push({source,operator,target,value,required});
 }
 if(!list.length||list.length>30)throw Error('1〜30ルールを指定してください。');
 return list;
}
async function init(){
 try{
  const app=kintone.app.getId();if(!app)throw Error('アプリIDを取得できません。');
  const resp=await kintone.api(kintone.api.url('/k/v1/app/form/fields.json',true),'GET',{app});
  fields=Object.values(resp.properties||{}).filter(f=>f.code).map(f=>({code:f.code,label:f.label||f.code,type:f.type}));
  fields.sort((a,b)=>a.label.localeCompare(b.label,'ja'));
  for(const item of saved)ruleLine(item);
  if(!saved.length)ruleLine();
 }catch(err){$('ra-error').textContent='フィールド取得エラー：'+(err.message||err);}
}
$('ra-add').addEventListener('click',()=>ruleLine());
$('ra-cancel').addEventListener('click',()=>window.history.back());
$('ra-form').addEventListener('submit',e=>{
 e.preventDefault();$('ra-error').textContent='';
 try{
  const rules=readRules();
  $('ra-save').disabled=true;
  kintone.plugin.app.setConfig({rules:JSON.stringify(rules)});
 }catch(err){$('ra-error').textContent=err.message||String(err);}
});
init();
})(kintone.$PLUGIN_ID);
