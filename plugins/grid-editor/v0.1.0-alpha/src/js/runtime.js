/* ResoArc grid editing experimental alpha: explicit preview and revision-checked update */
(function(pid){
'use strict';
const core=typeof ResoArcGrid==='undefined'?null:ResoArcGrid;
const cfg=kintone.plugin.app.getConfig(pid)||{};
const settings=core&&core.normalize(cfg.rules);
if(!settings)return;
function add(tag,text,parent){const node=document.createElement(tag);node.textContent=text;parent.appendChild(node);return node;}
function onShow(e){
 if(e.type!=='app.record.index.show')return e;
 const holder=kintone.app&&kintone.app.getHeaderSpaceElement&&kintone.app.getHeaderSpaceElement();
 if(!holder)return e;
 const old=holder.querySelector('#resoarc-grid-alpha');if(old)old.remove();
 const records=(e.records||[]).slice(0,settings.limit);
 const panel=add('section','',holder);panel.id='resoarc-grid-alpha';panel.style.cssText='padding:16px;background:#f7f9fa;border:1px solid #aab7c3;margin:12px 0';
 add('h3','ResoArc 一覧編集 α（リビジョン検査付き）',panel);
 add('p','現在表示中のレコードのみ。変更前プレビューと確認後に単一フィールドを更新します。部分成功の取り消しは行いません。',panel);
 const table=add('table','',panel);const head=add('tr','',table);
 ['ID','現在値','更新する値'].forEach(v=>add('th',v,head));
 const editors=new Map();
 records.forEach(r=>{
  const id=r.$id&&r.$id.value,value=r[settings.field]&&r[settings.field].value;
  if(!/^\d+$/.test(String(id))||value==null||typeof value==='object')return;
  const tr=add('tr','',table);
  add('td',String(id),tr);add('td',String(value),tr);
  const td=add('td','',tr),input=add('input','',td);
  input.type='text';input.value=String(value);input.maxLength=5000;
  editors.set(String(id),input);
 });
 const status=add('p','プレビュー未実行',panel);status.setAttribute('role','status');
 const previewButton=add('button','変更をプレビュー',panel);
 const apply=add('button','確認して更新',panel);apply.disabled=true;
 let staged=null;
 editors.forEach(input=>input.addEventListener('input',()=>{staged=null;apply.disabled=true;status.textContent='変更内容が変わりました。再プレビューしてください。';}));
 previewButton.addEventListener('click',()=>{
  const input=Object.fromEntries([...editors].map(([id,node])=>[id,node.value]));
  try{staged=core.preview(records,settings.field,input);status.textContent=JSON.stringify(staged.changes,null,2)||'変更なし';apply.disabled=staged.changedCount===0;}
  catch(err){status.textContent=err.message;staged=null;apply.disabled=true;}
 });
 apply.addEventListener('click',async()=>{
  if(!staged||!staged.changedCount||!window.confirm(staged.changedCount+'件の更新を実行しますか？'))return;
  apply.disabled=true;previewButton.disabled=true;
  let succeeded=0;
  const app=kintone.app.getId();
  try{
   for(const change of staged.changes){
    await kintone.api(kintone.api.url('/k/v1/record.json',true),'PUT',{app,id:change.id,revision:change.revision,record:{[settings.field]:{value:change.after}}});
    succeeded++;
   }
   status.textContent=succeeded+'件を更新しました。再読み込みして最新状態を確認してください。';
  }catch(err){status.textContent=succeeded+'件を更新した後に停止。未完了・競合の可能性があります: '+(err.message||err);}
 });
 return e;
}
kintone.events.on('app.record.index.show',onShow);
})(kintone.$PLUGIN_ID);
