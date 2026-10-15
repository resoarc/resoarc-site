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

/* ResoArc Conditional Fields runtime v0.1.0-alpha / SPDX-License-Identifier: MIT */
(function(pluginId){
'use strict';
const raw = kintone.plugin.app.getConfig(pluginId) || {};
const core = typeof ResoArcConditional === 'undefined' ? null : ResoArcConditional;
const rules = core && core.normalize(raw.rules);
if (!rules) return;
const ownError='この条件では入力が必要です。';
const editing=['app.record.create','app.record.edit','mobile.app.record.create','mobile.app.record.edit'];
const detail=['app.record.detail.show','mobile.app.record.detail.show'];
function getApi(event) {
  return event.type.startsWith('mobile.') ? kintone.mobile?.app?.record : kintone.app?.record;
}
function shown(event) {
  try {
    const api = getApi(event);
    if (typeof api?.setFieldShown !== 'function') return event;
    for (const r of core.evaluate(rules,event.record)) {
      if (r.missing || !event.record[r.target]) {
        console.warn('[ResoArc Conditional] Missing source or target field:',r.target);
        continue;
      }
      api.setFieldShown(r.target,r.shown);
    }
  } catch(err) {
    console.error('[ResoArc Conditional] Visibility update failed:',err);
  }
  return event;
}
kintone.events.on([...editing.map(p=>p+'.show'),...detail],shown);
for (const driver of new Set(rules.map(r=>r.source))) {
  kintone.events.on(editing.map(p=>p+'.change.'+driver),shown);
}
kintone.events.on(editing.map(p=>p+'.submit'),event=>{
  try {
    // Fail closed if configuration references a deleted/inaccessible field:
    // it must not silently bypass required validation.
    const states = core.evaluate(rules,event.record);
    if (states.some(state=>state.missing || !event.record[state.target])) {
      event.error='条件付き表示の対象フィールドを確認できません。アプリ設定と権限をご確認ください。';
      return event;
    }
    const api=getApi(event);
    for (const state of states) {
      const target=event.record[state.target];
      if (state.required && core.empty(target.value)) {
        if(typeof api?.setFieldShown==='function')api.setFieldShown(state.target,true);
        target.error=ownError;
      } else if (target.error===ownError) {
        target.error=null;
      }
      // Do not clear hidden values or override validation errors from other apps.
    }
  } catch(err) {
    console.error('[ResoArc Conditional] Required validation failed:',err);
    event.error='条件付き入力チェックを完了できませんでした。';
  }
  return event;
});
})(kintone.$PLUGIN_ID);
