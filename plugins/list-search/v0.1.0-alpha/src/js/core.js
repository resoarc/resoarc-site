/* ResoArc page-local search, pure core / MIT */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcListSearch=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
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
function readable(value) {
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
return {normalize,filter,readable};
});
