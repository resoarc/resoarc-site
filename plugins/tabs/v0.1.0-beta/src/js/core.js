/* ResoArc Field Tabs v0.1.0-beta / SPDX-License-Identifier: MIT */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcTabs=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const MAX_TABS=12,MAX_FIELDS=100;
function normalize(raw){
 let value;try{value=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(value)||!value.length||value.length>MAX_TABS)return null;
 let seen=new Set(),fields=0;
 let tabs=[];
 for(const entry of value){
   if(!entry||typeof entry!=='object')return null;
   const label=String(entry.label||'').trim();
   const codeList=entry.fields;
   if(!label||label.length>30||!Array.isArray(codeList)||!codeList.length)return null;
   const group=[];
   for(const code of codeList){
     if(typeof code!=='string'||!code.trim()||code.length>128||seen.has(code))return null;
     seen.add(code);group.push(code);fields++;if(fields>MAX_FIELDS)return null;
   }
   tabs.push({label,fields:group});
 }
 return tabs;
}
function plan(tabs,active){
 const normalized=normalize(tabs);
 if(!normalized||!Number.isInteger(active)||active<0||active>=normalized.length)throw Error('タブ設定に問題があります。');
 const all=normalized.flatMap(t=>t.fields);
 const visible=new Set(normalized[active].fields);
 return all.map(field=>({field,shown:visible.has(field)}));
}
return {normalize,plan};
});
