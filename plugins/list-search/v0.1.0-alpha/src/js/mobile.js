/* ResoArc bounded, permission-respecting list search. MIT */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcListSearch=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const MAX_SCAN=2000, PAGE_SIZE=500;
const safeCode=v=>typeof v==='string'&&v.length>=1&&v.length<=128&&!/[\u0000-\u001f]/.test(v);
function normalize(raw){
 let rules;try{rules=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(rules)||rules.length<1||rules.length>8)return null;
 const fields=new Set();
 for(const r of rules){
  if(!r||!safeCode(r.code)||fields.has(r.code)||!['contains','equals','startsWith'].includes(r.operator||'contains'))return null;
  fields.add(r.code);
 }
 return rules.map(r=>({code:r.code,label:String(r.label||r.code).slice(0,100),operator:r.operator||'contains'}));
}
function readable(value){
 if(value==null)return '';
 if(Array.isArray(value))return value.map(readable).join(', ');
 if(typeof value==='object')return value.name||value.code||JSON.stringify(value);
 return String(value);
}
function filter(records,rule,term){
 if(!Array.isArray(records)||!rule||!safeCode(rule.code))throw Error('一覧または検索設定が不正です');
 const query=String(term||'').normalize('NFKC').toLowerCase().trim();
 if(!query)return records.slice();
 if(query.length>200)throw Error('検索語が長すぎます');
 return records.filter(record=>{
  const v=record&&record[rule.code];
  const value=readable(v&&typeof v==='object'&&!Array.isArray(v)&&'value' in v?v.value:v).normalize('NFKC').toLowerCase();
  switch(rule.operator){case 'equals':return value===query;case 'startsWith':return value.startsWith(query);default:return value.includes(query);}
 });
}
function buildQuery(condition,lastId,size){
 if(condition===null||typeof condition!=='string'||condition.length>12000)throw Error('一覧の絞り込み条件が取得できません');
 if(!Number.isInteger(size)||size<1||size>PAGE_SIZE)throw Error('取得件数が不正です');
 if(lastId!==null&&(!/^[1-9]\d{0,15}$/.test(String(lastId))))throw Error('レコード番号が不正です');
 const where=[];
 if(condition.trim())where.push('('+condition.trim()+')');
 if(lastId!==null)where.push('($id > '+lastId+')');
 return (where.length?where.join(' and ')+' ':'')+'order by $id asc limit '+size;
}
async function scan(fetchPage,{condition,field,maxRecords=MAX_SCAN,shouldStop=()=>false,onProgress=()=>{}}){
 if(typeof fetchPage!=='function'||!safeCode(field)||!Number.isInteger(maxRecords)||maxRecords<1||maxRecords>MAX_SCAN)throw Error('検索範囲の設定が不正です');
 const records=[];let lastId=null,possiblyTruncated=false;
 while(records.length<maxRecords){
  if(shouldStop())throw Error('検索が中止されました');
  const size=Math.min(PAGE_SIZE,maxRecords-records.length);
  const query=buildQuery(condition,lastId,size);
  const response=await fetchPage({query,fields:['$id',field]});
  if(shouldStop())throw Error('検索が中止されました');
  const batch=response&&response.records;
  if(!Array.isArray(batch)||batch.length>size)throw Error('APIのレコード形式が不正です');
  for(const row of batch){
   const id=row&&row.$id&&String(row.$id.value);
   if(!id||! /^[1-9]\d{0,15}$/.test(id)||lastId!==null&&BigInt(id)<=BigInt(lastId))throw Error('レコード順序が不正です。更新後に再試行してください');
   lastId=id;records.push(row);
  }
  onProgress(records.length);
  possiblyTruncated=batch.length===size;
  if(batch.length<size)break;
 }
 return {records,scanned:records.length,possiblyTruncated,limit:maxRecords};
}
return {normalize,filter,readable,buildQuery,scan,MAX_SCAN,PAGE_SIZE};
});

/* ResoArc list search alpha: current page, or opt-in bounded scan of current view */
(function(pid){
'use strict';
const core=typeof ResoArcListSearch==='undefined'?null:ResoArcListSearch;
const cfg=kintone.plugin.app.getConfig(pid)||{};
const rules=core&&core.normalize(cfg.rules);
if(!rules)return;
let activeToken=0;
function add(tag,label,parent){
 const el=document.createElement(tag);el.textContent=label;parent.appendChild(el);return el;
}
function onShow(event){
 ++activeToken;
 const mobile=event.type.startsWith('mobile.');
 const api=mobile?kintone.mobile&&kintone.mobile.app:kintone.app;
 if(!api||typeof api.getHeaderSpaceElement!=='function')return event;
 const holder=api.getHeaderSpaceElement();if(!holder)return event;
 const old=holder.querySelector('#resoarc-search-alpha');if(old)old.remove();
 const panel=add('section','',holder);panel.id='resoarc-search-alpha';
 panel.style.cssText='margin:10px 0;padding:14px;border:1px solid #a5b8ba;background:#f8fbfb';
 add('h3','ResoArc 検索・絞り込み α',panel);
 const fieldSelect=document.createElement('select');fieldSelect.setAttribute('aria-label','検索フィールド');
 rules.forEach((r,i)=>{const o=add('option',r.label,fieldSelect);o.value=String(i);});panel.appendChild(fieldSelect);
 const input=document.createElement('input');input.type='search';input.maxLength=200;
 input.setAttribute('aria-label','検索語');input.placeholder='検索キーワード';panel.appendChild(input);
 const scope=document.createElement('select');scope.setAttribute('aria-label','検索範囲');
 for(const [value,label] of [['page','現在の表示ページだけ'],['view','一覧の絞り込み条件（最大2,000件）']]){
  const o=add('option',label,scope);o.value=value;
 }
 panel.appendChild(scope);
 add('p','初期設定は表示ページだけを検索します。広域検索はボタンを押した場合のみ、kintoneに最大2,000件を読み取りに行きます。データは外部へ送信しません。',panel);
 const button=add('button','検索',panel);button.type='button';
 const cancel=add('button','取得を中止',panel);cancel.type='button';cancel.hidden=true;
 const status=add('p','検索条件を入力してください',panel);status.setAttribute('role','status');
 const result=add('div','',panel);result.setAttribute('aria-live','polite');
 function invalidate(){activeToken++;button.disabled=false;cancel.hidden=true;}
 fieldSelect.addEventListener('change',invalidate);input.addEventListener('input',invalidate);scope.addEventListener('change',invalidate);
 cancel.addEventListener('click',()=>{invalidate();status.textContent='取得を中止しました';});
 function render(records,selected,scanned,description){
  result.replaceChildren();
  const matched=core.filter(records,selected,input.value);
  add('p',matched.length+' / '+scanned+' 件（'+description+'）',result);
  const ul=add('ul','',result);
  matched.slice(0,100).forEach(r=>{
   const id=r.$id&&r.$id.value;
   add('li',(id?'#'+id+' ':'')+core.readable(r[selected.code]&&r[selected.code].value),ul);
  });
  if(matched.length>100)add('p','表示は先頭100件までです。',result);
 }
 async function search(){
  invalidate();
  const token=activeToken,selected=rules[Number(fieldSelect.value)];
  if(!selected)return;
  if(scope.value==='page'){
   const data=Array.isArray(event.records)?event.records:[];
   try{render(data,selected,data.length,'現在の表示ページ');status.textContent='ページ内の検索完了';}
   catch(e){status.textContent=e.message;}
   return;
  }
  if(!input.value.trim()){status.textContent='広域検索では検索語を入力してください';return;}
  if(!api.getQueryCondition||!api.getId||typeof kintone.api!=='function'){status.textContent='一覧条件の取得APIを利用できません';return;}
  const condition=api.getQueryCondition();
  if(condition===null){status.textContent='この一覧から絞り込み条件を取得できません';return;}
  const app=api.getId();
  if(!app){status.textContent='アプリ番号が取得できません';return;}
  button.disabled=true;cancel.hidden=false;result.replaceChildren();status.textContent='一覧の条件を取得中...';
  try{
   const outcome=await core.scan(
    req=>kintone.api(kintone.api.url('/k/v1/records.json',true),'GET',{app,query:req.query,fields:req.fields}),
    {condition,field:selected.code,shouldStop:()=>token!==activeToken,
     onProgress:n=>{if(token===activeToken)status.textContent=n+'件読み込みました...';}}
   );
   if(token!==activeToken)return;
   render(outcome.records,selected,outcome.scanned,
     '現在の一覧条件・最大2,000件'+(outcome.possiblyTruncated?'／上限に達したため以降の有無は未確認':''));
   status.textContent='検索完了。'+(outcome.possiblyTruncated?'上限2,000件に達しました。以降は未確認です。':'');
  }catch(error){
   if(token!==activeToken)return;
   result.replaceChildren();status.textContent='検索できませんでした: '+(error.message||error);
  }finally{
   if(token===activeToken){button.disabled=false;cancel.hidden=true;}
  }
 }
 button.addEventListener('click',search);
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();search();}});
 return event;
}
kintone.events.on(['app.record.index.show','mobile.app.record.index.show'],onShow);
})(kintone.$PLUGIN_ID);
