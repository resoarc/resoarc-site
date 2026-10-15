/* ResoArc kanban alpha: read-only current-page visualization */
(function(pid){
'use strict';
const core=typeof ResoArcKanban==='undefined'?null:ResoArcKanban;
const cfg=kintone.plugin.app.getConfig(pid)||{};
const settings=core&&core.normalize(cfg.rules);
if(!settings)return;
function elem(name,text,parent){const node=document.createElement(name);node.textContent=text;parent.appendChild(node);return node;}
function show(event){
 const mobile=event.type.startsWith('mobile.');
 const api=mobile?kintone.mobile&&kintone.mobile.app:kintone.app;
 if(!api||typeof api.getHeaderSpaceElement!=='function')return event;
 const header=api.getHeaderSpaceElement();if(!header)return event;
 const prior=header.querySelector('#resoarc-kanban-alpha');if(prior)prior.remove();
 const panel=elem('section','',header);panel.id='resoarc-kanban-alpha';panel.style.cssText='padding:16px;border:1px solid #a7b2b7;margin:12px 0';
 elem('h3','ResoArc カンバン（読み取り専用・現在の表示ページ）',panel);
 const data=core.groups(event.records||[],settings);
 if(data.truncated)elem('p','表示上限により一部のレコードは省略されています。',panel);
 const layout=elem('div','',panel);layout.style.cssText='display:flex;gap:12px;overflow-x:auto;align-items:flex-start';
 const appId=String(api.getId&&api.getId()||'');
 for(const group of data.groups){
  const col=elem('section','',layout);col.style.cssText='min-width:205px;max-width:280px;flex:0 0 auto;padding:10px;border:1px solid #b1c3c6;background:#f7fafb';
  elem('h4',group.name+' ('+group.records.length+')',col);
  group.records.forEach(item=>{
   const card=elem('div',item.label||'(無題)',col);
   card.style.cssText='background:#fff;border:1px solid #d1d9db;padding:9px;margin:6px 0;overflow-wrap:anywhere';
   if(/^\d+$/.test(item.id)&&/^\d+$/.test(appId)){
    const link=elem('a','詳細を開く',card);link.href='/k/'+appId+'/show#record='+item.id;
   }
  });
 }
 return event;
}
kintone.events.on(['app.record.index.show','mobile.app.record.index.show'],show);
})(kintone.$PLUGIN_ID);
