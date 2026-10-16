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
