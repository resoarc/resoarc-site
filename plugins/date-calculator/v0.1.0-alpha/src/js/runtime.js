/* ResoArc Date Calculator alpha runtime / MIT */
(function(pid){
'use strict';
const core=typeof ResoArcDates==='undefined'?null:ResoArcDates;
const config=kintone.plugin.app.getConfig(pid)||{};
const rules=core&&core.normalize(config.rules);
if(!rules)return;
const bases=['app.record.create','app.record.edit','mobile.app.record.create','mobile.app.record.edit'];
const shows=bases.map(v=>v+'.show');
const changes=[...new Set(rules.flatMap(r=>[r.start,r.end]))].flatMap(f=>bases.map(v=>v+'.change.'+f));
function handler(event){
 if(!event||!event.record)return event;
 const values=core.evaluate(rules,event.record);
 for(const item of values){
  if(item.missing)continue;
  const target=event.record[item.target];
  if(item.error){target.error='ResoArc: '+item.error;continue;}
  if(target.error&&target.error.startsWith('ResoArc:'))delete target.error;
  if(item.skip)continue;
  // Erase obsolete calculations when a source date is cleared.
  target.value=item.value;
 }
 return event;
}
kintone.events.on([...shows,...changes],handler);
})(kintone.$PLUGIN_ID);
