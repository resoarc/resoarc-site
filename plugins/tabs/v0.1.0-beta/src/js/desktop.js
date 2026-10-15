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

/* ResoArc Field Tabs runtime v0.1.0-beta / SPDX-License-Identifier: MIT */
(function(pluginId){
'use strict';
const config=kintone.plugin.app.getConfig(pluginId)||{};
const core=typeof ResoArcTabs==='undefined'?null:ResoArcTabs;
const tabs=core&&core.normalize(config.tabs);
if(!tabs)return;
const spaceId=String(config.space||'resoarc_tabs');
const types=['app.record.create.show','app.record.edit.show','app.record.detail.show',
 'mobile.app.record.create.show','mobile.app.record.edit.show','mobile.app.record.detail.show'];
function getApi(isMobile){
 return isMobile?kintone.mobile&&kintone.mobile.app&&kintone.mobile.app.record
                :kintone.app&&kintone.app.record;
}
function tabBar(space,api){
 const previous=space.querySelector('[data-resoarc-tabs]');
 if(previous)previous.remove();
 const group=document.createElement('div');
 group.className='ra-tabs';group.setAttribute('data-resoarc-tabs','');
 group.setAttribute('role','tablist');
 group.setAttribute('aria-label','入力セクション');
 const buttons=[];
 let active=0;
 function activate(index){
   for(const item of core.plan(tabs,index))api.setFieldShown(item.field,item.shown);
   buttons.forEach((button,i)=>{
     button.setAttribute('aria-selected',String(i===index));
     button.tabIndex=i===index?0:-1;
   });
   active=index;
 }
 for(let i=0;i<tabs.length;i++){
   const b=document.createElement('button');
   b.className='ra-tab';b.type='button';b.textContent=tabs[i].label;
   b.setAttribute('role','tab');b.setAttribute('aria-selected','false');
   b.addEventListener('click',()=>activate(i));
   b.addEventListener('keydown',e=>{
     if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;
     e.preventDefault();
     const to=e.key==='Home'?0:e.key==='End'?buttons.length-1:e.key==='ArrowRight'?(active+1)%buttons.length:(active+buttons.length-1)%buttons.length;
     activate(to);buttons[to].focus();
   });
   group.appendChild(b);buttons.push(b);
 }
 const all=document.createElement('button');all.type='button';all.textContent='すべて表示';
 all.className='ra-tab-all';all.setAttribute('aria-label','すべてのフィールドを表示');
 all.addEventListener('click',()=>{
   for(const t of tabs)for(const f of t.fields)api.setFieldShown(f,true);
   buttons.forEach(button=>{button.setAttribute('aria-selected','false');button.tabIndex=0;});
 });
 group.appendChild(all);space.appendChild(group);activate(0);
}
kintone.events.on(types,event=>{
 try{
  const mobile=event.type.startsWith('mobile.');
  const api=getApi(mobile);
  if(!api||typeof api.setFieldShown!=='function'||typeof api.getSpaceElement!=='function')return event;
  const space=api.getSpaceElement(spaceId);
  if(!space){console.warn('[ResoArc Tabs] Space field not found:',spaceId);return event;}
  tabBar(space,api);
 }catch(err){console.error('[ResoArc Tabs] Unable to initialize tabs:',err);}
 return event;
});
kintone.events.on(['app.record.create.submit','app.record.edit.submit','mobile.app.record.create.submit','mobile.app.record.edit.submit'],event=>{
 try{
  const api=getApi(event.type.startsWith('mobile.'));
  if(api&&typeof api.setFieldShown==='function')for(const tab of tabs)for(const field of tab.fields)api.setFieldShown(field,true);
 }catch(err){console.error('[ResoArc Tabs] Restore visibility failed:',err);}
 return event;
});
})(kintone.$PLUGIN_ID);
