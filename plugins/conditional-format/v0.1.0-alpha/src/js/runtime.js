/* ResoArc Conditional Formatting 0.1.0-alpha / MIT */
(function(pluginId){
'use strict';
const core=typeof ResoArcFormatting==='undefined'?null:ResoArcFormatting;
const config=kintone.plugin.app.getConfig(pluginId)||{};
const rules=core&&core.normalize(config.rules);
if(!rules)return;
const bases=['app.record.create','app.record.edit','mobile.app.record.create','mobile.app.record.edit'];
const shows=[...bases.map(x=>x+'.show'),'app.record.detail.show','mobile.app.record.detail.show'];
const changes=[...new Set(rules.map(r=>r.source))].flatMap(code=>bases.map(x=>x+'.change.'+code));
// Async styling is isolated from synchronous kintone change event returns.
// A per-field promise queue ensures a stale request cannot overwrite a newer one.
const queues=new Map();
function getApi(event){return event.type.startsWith('mobile.')?kintone.mobile?.app?.record:kintone.app?.record;}
function render(event){
 const api=getApi(event);
 if(typeof api?.setFieldStyle!=='function')return event;
 let computed;
 try{computed=core.evaluate(rules,event.record);}
 catch(err){console.error('[ResoArc Formatting] invalid rule:',err);return event;}
 for(const state of computed){
  if(state.missing)continue; // protect hidden or inaccessible fields
  const prev=queues.get(state.target)||Promise.resolve();
  const next=prev.catch(()=>{}).then(()=>api.setFieldStyle(state.target,state.style));
  queues.set(state.target,next);
  next.catch(err=>console.warn('[ResoArc Formatting] field style skipped:',state.target,err));
 }
 return event;
}
kintone.events.on([...shows,...changes],render);
})(kintone.$PLUGIN_ID);
