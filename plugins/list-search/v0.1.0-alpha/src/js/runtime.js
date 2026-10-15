/* ResoArc list search alpha / current list page only */
(function(pid){
'use strict';
const core=typeof ResoArcListSearch==='undefined'?null:ResoArcListSearch;
const cfg=kintone.plugin.app.getConfig(pid)||{};
const rules=core&&core.normalize(cfg.rules);
if(!rules)return;
function add(tag,text,parent){const el=document.createElement(tag);el.textContent=text;parent.appendChild(el);return el;}
function onShow(event){
 const mobile=event.type.startsWith('mobile.');
 const api=mobile?kintone.mobile&&kintone.mobile.app:kintone.app;
 if(!api||typeof api.getHeaderSpaceElement!=='function')return event;
 const holder=api.getHeaderSpaceElement();
 if(!holder)return event;
 const old=holder.querySelector('#resoarc-search-alpha');if(old)old.remove();
 const panel=document.createElement('section');panel.id='resoarc-search-alpha';
 panel.style.cssText='margin:10px 0;padding:14px;border:1px solid #a5b8ba;background:#f8fbfb';
 add('h3','ResoArc 一覧内検索（現在の表示ページのみ）',panel);
 const select=document.createElement('select');select.setAttribute('aria-label','検索フィールド');
 rules.forEach((r,i)=>{const o=add('option',r.label,select);o.value=String(i);});panel.appendChild(select);
 const input=document.createElement('input');input.type='search';input.maxLength=200;input.setAttribute('aria-label','検索語');input.placeholder='検索キーワード';panel.appendChild(input);
 const button=add('button','検索',panel);button.type='button';
 const result=add('div','',panel);result.setAttribute('aria-live','polite');
 function render(){
  result.replaceChildren();
  const selected=rules[Number(select.value)];
  let matched;try{matched=core.filter(event.records||[],selected,input.value);}catch(e){add('p',e.message,result);return;}
  add('p',matched.length+' / '+(event.records||[]).length+' 件（現在の一覧ページ）',result);
  const list=add('ul','',result);
  matched.slice(0,100).forEach(r=>add('li',core.readable(r[selected.code]&&r[selected.code].value),list));
 }
 button.addEventListener('click',render);input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();render();}});
 holder.appendChild(panel);
 return event;
}
kintone.events.on(['app.record.index.show','mobile.app.record.index.show'],onShow);
})(kintone.$PLUGIN_ID);
