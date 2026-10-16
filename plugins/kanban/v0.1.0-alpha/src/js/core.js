/* ResoArc read-only kanban grouping / MIT */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.ResoArcKanban=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
function normalize(raw){
 let list;try{list=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return null;}
 if(!Array.isArray(list)||list.length!==1)return null;
 const r=list[0];
 if(!r||typeof r.groupField!=='string'||!r.groupField||typeof r.labelField!=='string'||!r.labelField||r.groupField.length>128||r.labelField.length>128)return null;
 const limit=Number(r.limit==null?60:r.limit);
 if(!Number.isInteger(limit)||limit<1||limit>100)return null;
 return {groupField:r.groupField,labelField:r.labelField,limit};
}
function text(v){
 if(v==null)return '';
 if(typeof v==='object'&&'value' in v)return text(v.value);
 if(Array.isArray(v))return v.map(text).join('、');
 if(typeof v==='object')return v.name||v.code||JSON.stringify(v);
 return String(v);
}
function groups(rows,config){
 if(!Array.isArray(rows)||!config)throw Error('レコードまたは設定が不正です');
 const out=new Map(),slice=rows.slice(0,config.limit);
 for(const record of slice){
  const value=text(record[config.groupField])||'(空欄)';
  if(!out.has(value))out.set(value,[]);
  out.get(value).push({id:text(record.$id),label:text(record[config.labelField])});
 }
 return {shown:slice.length,truncated:rows.length>slice.length,groups:[...out].map(([name,records])=>({name,records}))};
}
function recordLink(pathname,appId,recordId,mobile){
 if(!/^[1-9][0-9]*$/.test(String(appId))||!/^[1-9][0-9]*$/.test(String(recordId)))return null;
 const path=typeof pathname==='string'?pathname:'';
 const match=new RegExp('^/k/guest/([1-9][0-9]*)(?:/|$)').exec(path);
 const prefix=match?'/k/guest/'+match[1]:'/k';
 return mobile?
  prefix+'/m/'+appId+'/show?record='+recordId:
  prefix+'/'+appId+'/show#record='+recordId;
}
return {normalize,text,groups,recordLink};
});
