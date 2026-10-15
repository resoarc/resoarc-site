/* ResoArc Conditional Fields 0.1.0-alpha / SPDX-License-Identifier: MIT */
(function(root,factory){'use strict';const out=factory();if(typeof module==='object'&&module.exports)module.exports=out;if(root)root.ResoArcConditional=out;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const ops=new Set(['eq','neq','includes','empty','not_empty','gt','gte','lt','lte']);
function normalize(raw){
 let obj;try{obj=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(obj)||obj.length===0||obj.length>30)return null;
 const used=new Set(),result=[];
 for(const r of obj){
   if(!r||typeof r!=='object')return null;
   const source=String(r.source||''),target=String(r.target||''),operator=String(r.operator||'');
   const value=String(r.value??'');
   if(!source||!target||source===target||source.length>128||target.length>128||used.has(target)||!ops.has(operator)||value.length>256)return null;
   used.add(target);
   result.push({source,target,operator,value,required:!!r.required});
 }
 return result;
}
function empty(value){
 if(value===null||typeof value==='undefined')return true;
 if(typeof value==='string')return value.trim()==='';
 if(Array.isArray(value))return value.length===0;
 return false;
}
function match(rule,input){
 const op=rule.operator;
 if(op==='empty')return empty(input);
 if(op==='not_empty')return !empty(input);
 if(empty(input))return false;
 if(Array.isArray(input)){
   if(op==='includes')return input.some(x=>String(x)===rule.value);
   return (op==='eq'?input.some(x=>String(x)===rule.value):op==='neq'?input.every(x=>String(x)!==rule.value):false);
 }
 const a=String(input),b=rule.value;
 if(op==='eq')return a===b;
 if(op==='neq')return a!==b;
 if(op==='includes')return a.includes(b);
 if(['gt','gte','lt','lte'].includes(op)){
   const x=Number(a),y=Number(b);
   if(!Number.isFinite(x)||!Number.isFinite(y)||b.trim()==='')return false;
   return op==='gt'?x>y:op==='gte'?x>=y:op==='lt'?x<y:x<=y;
 }
 return false;
}
function evaluate(rules,record){
 const valid=normalize(rules);
 if(!valid||!record)throw Error('条件設定が不正です。');
 return valid.map(rule=>{
   const field=record[rule.source];
   if(!field)return {target:rule.target,missing:true,shown:true,required:false};
   const shown=match(rule,field.value);
   return {target:rule.target,missing:false,shown,required:shown&&rule.required};
 });
}
return {normalize,empty,match,evaluate};
});
