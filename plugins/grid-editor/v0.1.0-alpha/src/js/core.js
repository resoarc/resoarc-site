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
