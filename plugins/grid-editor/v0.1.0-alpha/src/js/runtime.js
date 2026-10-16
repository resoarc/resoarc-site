/* ResoArc grid editor experimental alpha: preview, type and revision checks */
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
 add('p','現在の一覧ページのみ編集可能。変更前の差分確認とリビジョン検査を実施します。更新の取り消しはできません。',panel);
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
  let succeeded=0;const ids=[];
  try{
   const app=kintone.app.getId();
   if(!app)throw Error('アプリIDを取得できません');
   for(const change of staged.changes){
    status.textContent='更新中: '+succeeded+'/'+staged.changedCount+' 件';
    await kintone.api(kintone.api.url('/k/v1/record.json',true),'PUT',{
     app,id:change.id,revision:change.revision,record:{[settings.field]:{value:change.after}}
    });
    succeeded++;ids.push(change.id);
   }
   status.textContent='完了: '+succeeded+'件更新しました。ID: '+ids.join(', ')+'。ページを再読込してください。';
  }catch(error){
   status.textContent='途中停止: 成功 '+succeeded+'件（ID: '+ids.join(', ')+ '）。失敗以降のレコードは未処理です。原因: '+(error.message||error)+'。再読込して状態を確認してください。';
  }finally{
   settled=true; // No second write from stale revisions. Reload to retry.
  }
 });
 return e;
}
kintone.events.on('app.record.index.show',onShow);
})(kintone.$PLUGIN_ID);
