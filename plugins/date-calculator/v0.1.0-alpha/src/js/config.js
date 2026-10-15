/* ResoArc field-based settings UI / MIT */
(function(pid){
'use strict';
const spec={"core":"ResoArcDates","min":1,"max":30,"fields":[{"key":"start","label":"開始日フィールドコード（DATE）","kind":"field"},{"key":"end","label":"終了日フィールドコード（DATE）","kind":"field"},{"key":"target","label":"出力先フィールドコード（数値・文字列）","kind":"field"},{"key":"mode","label":"日数の計算方法","kind":"select","options":[["calendar","暦日"],["business","営業日（土日除外）"]]},{"key":"holidays","label":"追加で除外する祝日 YYYY-MM-DD（改行かカンマで区切る）","kind":"dates"}],"defaults":{"start":"","end":"","target":"","mode":"calendar","holidays":[]}};
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
document.getElementById('save').addEventListener('click',()=>{
 alert.textContent='';
 try{
  const candidate=readRows();
  if(candidate.length<spec.min||candidate.length>spec.max||!core||!core.normalize(candidate)){
   throw Error('設定値が正しくありません。フィールドコード・重複・数値・日付を確認してください。');
  }
  kintone.plugin.app.setConfig({rules:JSON.stringify(candidate)});
  note.textContent='設定を保存しました。アプリの設定を更新して適用してください。';
 }catch(e){alert.textContent=e.message||String(e);}
});
document.getElementById('cancel').addEventListener('click',()=>history.back());
render();
// Lookup suggestions only. Settings must remain usable without this optional API permission.
try{
 const id=kintone.app&&kintone.app.getId&&kintone.app.getId();
 if(id&&typeof kintone.api==='function'){
  kintone.api(kintone.api.url('/k/v1/app/form/fields.json',true),'GET',{app:id}).then(data=>{
   for(const [code,info] of Object.entries(data.properties||{})){
    if(typeof code!=='string'||code.length>128)continue;
    const opt=document.createElement('option');opt.value=code;opt.textContent=String(info.label||code)+' ('+String(info.type||'')+')';fieldList.appendChild(opt);
   }
  }).catch(()=>{});
 }
}catch(_){}
})(kintone.$PLUGIN_ID);
