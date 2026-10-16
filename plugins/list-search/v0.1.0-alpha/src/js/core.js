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
