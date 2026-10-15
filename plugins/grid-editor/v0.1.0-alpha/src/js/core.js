/* ResoArc grid editor pure diff and revision safeguards / MIT */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcGrid=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
function normalize(raw) {
 let list;try{list=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(list)||list.length!==1)return null;
 const r=list[0];
 if(!r||typeof r.field!=='string'||!r.field.trim()||r.field.length>128||/[\u0000-\u001f]/.test(r.field))return null;
 const limit=Number(r.limit==null?30:r.limit);
 if(!Number.isInteger(limit)||limit<1||limit>100)return null;
 return {field:r.field,limit};
}
function preview(records,field,inputs){
 if(!Array.isArray(records)||!field||!inputs||typeof inputs!=='object')throw Error('編集条件が不正です');
 const seen=new Set(),changes=[];
 for(const record of records){
  const id=record&&record.$id&&record.$id.value;
  const rev=record&&record.$revision&&record.$revision.value;
  if(!/^\d+$/.test(String(id))||!/^\d+$/.test(String(rev)))throw Error('IDまたはリビジョンが取得できません');
  if(seen.has(String(id)))throw Error('レコードIDが重複しています');seen.add(String(id));
  const data=record[field];
  if(!data||!Object.prototype.hasOwnProperty.call(data,'value')||typeof data.value==='object')throw Error('編集対象は通常の文字列・数値フィールドに限定します');
  if(!Object.prototype.hasOwnProperty.call(inputs,String(id)))continue;
  const next=String(inputs[id]),current=String(data.value==null?'':data.value);
  if(next!==current)changes.push({id:String(id),revision:String(rev),field,before:current,after:next});
 }
 return {mode:'PREVIEW',field,recordCount:records.length,changedCount:changes.length,changes};
}
return {normalize,preview};
});
