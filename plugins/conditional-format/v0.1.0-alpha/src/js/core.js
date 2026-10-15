/* ResoArc Conditional Formatting 0.1.0-alpha | SPDX-License-Identifier: MIT
 * Pure evaluation and a fixed high-contrast palette. No user-provided CSS. */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcFormatting=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const operators=['eq','neq','includes','empty','not_empty','gt','gte','lt','lte'];
const themes={
 navy:{background:{backgroundColor:'#e8eff8'},content:{color:'#173653',fontWeight:'bold'}},
 amber:{background:{backgroundColor:'#fff2d8'},content:{color:'#6c4100',fontWeight:'bold'}},
 red:{background:{backgroundColor:'#fce8e8'},content:{color:'#801c23',fontWeight:'bold'}},
 green:{background:{backgroundColor:'#e6f2e9'},content:{color:'#205a36',fontWeight:'bold'}},
 gray:{background:{backgroundColor:'#edf0f3'},content:{color:'#37465a',fontWeight:'bold'}}
};
function normalize(raw){
 let src;try{src=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(src)||src.length<1||src.length>30)return null;
 const list=[],seen=new Set();
 for(const r of src){
  if(!r||typeof r!=='object')return null;
  const source=String(r.source||''),target=String(r.target||''),operator=String(r.operator||''),value=String(r.value??''),theme=String(r.theme||'');
  if(!source||!target||source.length>128||target.length>128||!operators.includes(operator)||!Object.hasOwn(themes,theme)||value.length>200||seen.has(target))return null;
  seen.add(target);list.push({source,target,operator,value,theme});
 }
 return list;
}
function empty(x){return x===null||typeof x==='undefined'||(typeof x==='string'&&x.trim()==='')||(Array.isArray(x)&&x.length===0);}
function match(rule,value){
 if(rule.operator==='empty')return empty(value);
 if(rule.operator==='not_empty')return !empty(value);
 if(empty(value))return false;
 const s=Array.isArray(value)?value.map(x=>String(x)):String(value);
 const b=rule.value;
 if(Array.isArray(s)){
  if(rule.operator==='includes'||rule.operator==='eq')return s.includes(b);
  if(rule.operator==='neq')return !s.includes(b);
  return false;
 }
 if(rule.operator==='eq')return s===b;
 if(rule.operator==='neq')return s!==b;
 if(rule.operator==='includes')return s.includes(b);
 if(['gt','gte','lt','lte'].includes(rule.operator)){
  if(s.trim()===''||b.trim()==='')return false;
  const a=Number(s),n=Number(b);
  if(!Number.isFinite(a)||!Number.isFinite(n))return false;
  if(rule.operator==='gt')return a>n;
  if(rule.operator==='gte')return a>=n;
  if(rule.operator==='lt')return a<n;
  return a<=n;
 }
 return false;
}
function evaluate(rules,record){
 const valid=normalize(rules);
 if(!valid||!record||typeof record!=='object')throw Error('設定またはレコードが不正です。');
 return valid.map(rule=>{
  const source=record[rule.source],target=record[rule.target];
  if(!source||!target)return {target:rule.target,missing:true,active:false,style:null};
  const active=match(rule,source.value);
  return {target:rule.target,missing:false,active,style:active?JSON.parse(JSON.stringify(themes[rule.theme])):'DEFAULT'};
 });
}
return {operators,themes,normalize,empty,match,evaluate};
});
