/* ResoArc Tabs config v0.1.0-beta / MIT */
(function(pluginId){
'use strict';
const $=id=>document.getElementById(id);
const holder=$('ra-tabs-settings'),error=$('ra-error'),old=kintone.plugin.app.getConfig(pluginId)||{};
const all=[];let current=[];
try{current=JSON.parse(old.tabs||'[]');if(!Array.isArray(current))current=[];}catch(_){current=[];}
$('ra-space').value=old.space||'resoarc_tabs';
function err(msg){error.textContent=msg||'';}
function entryEditor(entry){
 if(holder.children.length>=12){err('タブは最大12個です。');return;}
 const item=document.createElement('section');item.className='ra-tab-editor';
 const head=document.createElement('div');head.className='ra-tab-head';
 const label=document.createElement('label');label.textContent='タブ名';
 const input=document.createElement('input');input.maxLength=30;input.required=true;input.value=entry?.label||'';
 label.appendChild(input);
 const del=document.createElement('button');del.type='button';del.className='ra-secondary';del.textContent='このタブを削除';del.addEventListener('click',()=>item.remove());
 head.append(label,del);item.appendChild(head);
 const opt=document.createElement('div');opt.className='ra-field-options';
 const selected=new Set(entry?.fields||[]);
 for(const f of all){
   const label=document.createElement('label');
   const cb=document.createElement('input');cb.type='checkbox';cb.value=f.code;cb.checked=selected.has(f.code);
   const text=document.createElement('span');text.textContent=f.label+' ('+f.code+')';
   label.append(cb,text);opt.appendChild(label);
 }
 item.appendChild(opt);holder.appendChild(item);
}
function extract(){
 const tabs=[],seen=new Set();
 for(const section of holder.querySelectorAll('.ra-tab-editor')){
   const label=section.querySelector('input:not([type="checkbox"])').value.trim();
   const fields=[...section.querySelectorAll('input[type="checkbox"]:checked')].map(x=>x.value);
   if(!label||label.length>30||!fields.length)throw Error('すべてのタブに名前と1件以上のフィールドが必要です。');
   for(const code of fields){if(seen.has(code))throw Error('同じフィールドを複数のタブに割り当てることはできません。');seen.add(code);}
   tabs.push({label,fields});
 }
 if(!tabs.length||tabs.length>12||seen.size>100)throw Error('タブは1～12、フィールドは100件以内です。');
 return tabs;
}
async function init(){
 try{
  const app=kintone.app.getId();
  if(!app)throw Error('アプリIDを取得できません。');
  const result=await kintone.api(kintone.api.url('/k/v1/app/form/fields.json',true),'GET',{app});
  for(const f of Object.values(result.properties||{})){
   if(['SUBTABLE','GROUP','LABEL','SPACER','HR','REFERENCE_TABLE','RECORD_NUMBER','CREATED_TIME','UPDATED_TIME','CREATOR','MODIFIER','STATUS','STATUS_ASSIGNEE','CATEGORY'].includes(f.type))continue;
   if(f.type==='CALC'||f.type==='FILE')continue;
   if(!f.code)continue;
   all.push({code:f.code,label:f.label||f.code});
  }
  all.sort((a,b)=>a.label.localeCompare(b.label,'ja'));
  for(const t of current)entryEditor(t);
  if(!current.length)entryEditor({label:'基本情報',fields:[]});
  if(!all.length)err('設定できる通常フィールドが見つかりません。フィールドを追加してください。');
 }catch(e){err('フィールドを取得できません：'+(e.message||e));}
}
$('ra-add').addEventListener('click',()=>entryEditor({label:'',fields:[]}));
$('ra-cancel').addEventListener('click',()=>window.history.back());
$('ra-config-form').addEventListener('submit',e=>{
 e.preventDefault();err('');
 try{
  const space=$('ra-space').value.trim();
  if(!/^[a-zA-Z0-9_-]{1,128}$/.test(space))throw Error('スペース要素IDは半角英数字・ハイフン・アンダースコアです。');
  const tabs=extract();
  $('ra-save').disabled=true;
  kintone.plugin.app.setConfig({tabs:JSON.stringify(tabs),space});
 }catch(e){err(e.message||String(e));}
});
init();
})(kintone.$PLUGIN_ID);
