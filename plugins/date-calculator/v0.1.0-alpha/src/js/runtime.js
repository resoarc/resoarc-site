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
const submits=bases.map(v=>v+'.submit');
function handler(event){
 if(!event||!event.record)return event;
 const saving=typeof event.type==='string'&&event.type.endsWith('.submit');
 let values;
 try{values=core.evaluate(rules,event.record);}
 catch(error){
  if(saving)event.error='ResoArc 日付計算の設定を確認できません。保存を中止しました。';
  return event;
 }
 for(const item of values){
  if(item.missing){
   if(saving)event.error='ResoArc 日付計算のフィールド設定またはアクセス権が不正です。保存を中止しました。';
   continue;
  }
  const target=event.record[item.target];
  if(item.error){target.error='ResoArc: '+item.error;continue;}
  if(target.error&&target.error.startsWith('ResoArc:'))delete target.error;
  if(item.skip)continue;
  // Erase obsolete calculations when a source date is cleared.
  target.value=item.value;
 }
 return event;
}
kintone.events.on([...shows,...changes,...submits],handler);
})(kintone.$PLUGIN_ID);
