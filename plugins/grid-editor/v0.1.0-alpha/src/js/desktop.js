/* ResoArc grid editor pure diff, typed validation, revision safeguards. MIT */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcGrid=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const EDITABLE_TYPES=['SINGLE_LINE_TEXT','MULTI_LINE_TEXT','NUMBER'];
function normalize(raw){
 let list;try{list=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(list)||list.length!==1)return null;
 const r=list[0];
 if(!r||typeof r.field!=='string'||!r.field.trim()||r.field.length>128||/[\u0000-\u001f]/.test(r.field))return null;
 const limit=Number(r.limit==null?30:r.limit);
 if(!Number.isInteger(limit)||limit<1||limit>100)return null;
 return {field:r.field,limit};
}
function canEdit(field){
 return !!field&&EDITABLE_TYPES.includes(field.type)&&('value' in field)&&
  (field.value===null||typeof field.value==='string'||typeof field.value==='number');
}
function validateValue(field,value){
 if(typeof value!=='string'||value.length>5000)throw Error('入力は5,000文字以内の文字列にしてください');
 if(field.type==='NUMBER'){
  if(value.trim()!==value)throw Error('数値に前後の空白を含めないでください');
  if(value!==''&&(!/^-?(?:\d+(?:\.\d+)?|\.\d+)$/.test(value)||value.length>32))throw Error('数値フィールドには半角数字または小数を入力してください');
 }
 return value;
}
function preview(records,field,inputs){
 if(!Array.isArray(records)||!field||!inputs||typeof inputs!=='object')throw Error('編集条件が不正です');
 const seen=new Set(),changes=[];
 for(const record of records){
  const id=record&&record.$id&&record.$id.value;
  const rev=record&&record.$revision&&record.$revision.value;
  if(!/^\d+$/.test(String(id))||!/^\d+$/.test(String(rev)))throw Error('IDまたはリビジョンが取得できません');
  if(seen.has(String(id)))throw Error('レコードIDが重複しています');
  seen.add(String(id));
  const data=record[field];
  if(!canEdit(data))throw Error('更新可能な文字列・複数行文字列・数値フィールドだけが対象です');
  if(!Object.prototype.hasOwnProperty.call(inputs,String(id)))continue;
  const next=validateValue(data,inputs[String(id)]),current=String(data.value==null?'':data.value);
  if(next!==current)changes.push({id:String(id),revision:String(rev),field,before:current,after:next});
 }
 return {mode:'PREVIEW',field,recordCount:records.length,changedCount:changes.length,changes};
}
function batchRequest(plan,app){
 if(!plan||plan.mode!=='PREVIEW'||!Number.isInteger(plan.changedCount)||!Array.isArray(plan.changes)||plan.changes.length!==plan.changedCount||plan.changedCount<1||plan.changedCount>100)throw Error('一括更新は1～100件までです');
 if(!/^[1-9]\d*$/.test(String(app)))throw Error('アプリ番号が不正です');
 const ids=new Set();
 const records=plan.changes.map(change=>{
  if(!change||!/^\d+$/.test(change.id)||!/^\d+$/.test(change.revision)||ids.has(change.id)||change.field!==plan.field||typeof change.after!=='string')throw Error('変更プレビューが不正です');
  ids.add(change.id);
  return {id:change.id,revision:change.revision,record:{[change.field]:{value:change.after}}};
 });
 return {app,records};
}
function preflightRequest(plan,app){
 const payload=batchRequest(plan,app);
 const ids=payload.records.map(r=>r.id);
 return {
  app:payload.app,
  fields:['$id','$revision',plan.field],
  query:'$id in ('+ids.join(',')+') limit '+ids.length
 };
}
function confirmUnchanged(plan,response,app){
 const payload=batchRequest(plan,app);
 if(!response||!Array.isArray(response.records)||response.records.length!==plan.changedCount){
  throw Error('取得件数が変更プレビューと一致しません。更新は実行しません');
 }
 const read=new Map();
 for(const record of response.records){
  const id=record&&record.$id&&String(record.$id.value);
  if(!id||read.has(id))throw Error('取得したレコードIDが不正です。更新は実行しません');
  read.set(id,record);
 }
 for(const change of plan.changes){
  const live=read.get(change.id);
  if(!live)throw Error('更新対象のレコードが見つかりません: '+change.id);
  const revision=live.$revision&&String(live.$revision.value);
  const cell=live[change.field];
  if(!canEdit(cell)||revision!==change.revision||
      String(cell.value==null?'':cell.value)!==change.before){
   throw Error('レコード '+change.id+' の内容または更新権限が変更されています。再読込してください');
  }
 }
 return payload;
}
return {normalize,canEdit,validateValue,preview,batchRequest,preflightRequest,confirmUnchanged,EDITABLE_TYPES};
});

/* ResoArc grid editor experimental alpha: single atomic request, type and revision checks */
(function(pid){
'use strict';
const core=typeof ResoArcGrid==='undefined'?null:ResoArcGrid;
const cfg=kintone.plugin.app.getConfig(pid)||{};
const settings=core&&core.normalize(cfg.rules);
if(!settings)return;
function add(tag,value,parent){const el=document.createElement(tag);el.textContent=value;parent.appendChild(el);return el;}
function onShow(e){
 if(e.type!=='app.record.index.show'||(e.viewType&&e.viewType!=='list'))return e;
 const holder=kintone.app&&kintone.app.getHeaderSpaceElement&&kintone.app.getHeaderSpaceElement();
 if(!holder||!Array.isArray(e.records))return e;
 const old=holder.querySelector('#resoarc-grid-alpha');if(old)old.remove();
 const records=e.records.slice(0,settings.limit),eligible=[];
 const panel=add('section','',holder);panel.id='resoarc-grid-alpha';
 panel.style.cssText='padding:16px;background:#f7f9fa;border:1px solid #aab7c3;margin:12px 0';
 add('h3','ResoArc 一覧編集 α（文字列・数値のみ）',panel);
 add('p','現在の一覧ページのみ編集可能。最大100件を1回のAPIで一括更新します。1件でもエラーなら全件変更しません。更新成功後の取り消し機能はありません。',panel);
 const table=add('table','',panel),head=add('tr','',table);
 ['ID','現在値','更新する値'].forEach(v=>add('th',v,head));
 const editors=new Map();let skipped=0;
 records.forEach(r=>{
  const id=r&&r.$id&&r.$id.value, data=r&&r[settings.field];
  if(!/^\d+$/.test(String(id))||!core.canEdit(data)||!r.$revision){skipped++;return;}
  const tr=add('tr','',table);
  add('td',String(id),tr);add('td',String(data.value??''),tr);
  const td=add('td','',tr),input=add('input','',td);
  input.type='text';input.value=String(data.value??'');input.maxLength=5000;
  input.setAttribute('aria-label','レコード '+id+' の新しい値');
  editors.set(String(id),input);eligible.push(r);
 });
 if(skipped)add('p',skipped+'件のレコードは対象外です（編集不能フィールドまたはリビジョン未取得）。',panel);
 const status=add('p','変更を入力したらプレビューしてください',panel);status.setAttribute('role','status');
 const previewButton=add('button','変更をプレビュー',panel);previewButton.type='button';
 const apply=add('button','確認して更新',panel);apply.type='button';apply.disabled=true;
 let staged=null,busy=false,settled=false;
 function lock(){busy=true;apply.disabled=true;previewButton.disabled=true;editors.forEach(v=>v.disabled=true);}
 editors.forEach(input=>input.addEventListener('input',()=>{
  staged=null;apply.disabled=true;status.textContent='入力が変更されました。再プレビューしてください。';
 }));
 previewButton.addEventListener('click',()=>{
  if(busy||settled)return;
  const values=Object.fromEntries([...editors].map(([id,el])=>[id,el.value]));
  try{
   staged=core.preview(eligible,settings.field,values);
   status.textContent=staged.changedCount+'件の変更候補: '+JSON.stringify(staged.changes);
   apply.disabled=staged.changedCount===0;
  }catch(error){staged=null;apply.disabled=true;status.textContent=error.message;}
 });
 apply.addEventListener('click',async()=>{
  if(busy||settled||!staged||!staged.changedCount)return;
  if(!window.confirm(settings.field+' の '+staged.changedCount+'件を実際に更新します。取り消しできません。実行しますか？'))return;
  lock();
  let submitted=false;
  try{
   const app=kintone.app.getId();
   const request=core.preflightRequest(staged,app);
   status.textContent='更新直前の状態を確認中: '+staged.changedCount+'件';
   const current=await kintone.api(kintone.api.url('/k/v1/records.json',true),'GET',request);
   const payload=core.confirmUnchanged(staged,current,app);
   status.textContent='確認完了。一括更新リクエスト中: '+staged.changedCount+'件';
   submitted=true;
   await kintone.api(kintone.api.url('/k/v1/records.json',true),'PUT',payload);
   status.textContent='一括更新完了: '+staged.changedCount+'件。ページを再読込してください。';
  }catch(error){
   status.textContent=(submitted?
    'APIの応答に失敗しました。更新結果が不明な場合があります。再実行せず、画面を再読込して確認してください: ':
    '更新前の安全確認に失敗したため書き込みは行っていません。再読込して確認してください: ')+(error.message||error);
  }finally{
   settled=true; // A dropped PUT response is ambiguous; never retry automatically.
  }
 });
 return e;
}
kintone.events.on('app.record.index.show',onShow);
})(kintone.$PLUGIN_ID);
