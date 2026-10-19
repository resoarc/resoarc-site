/* ResoArc auto-generated public-site navigation. No third-party dependencies. */
(()=>{'use strict';
const ENDPOINT='/assets/navigation-map.json';
const normalize=raw=>{
 try {
  const url=new URL(raw,location.origin);
  let path=url.pathname.replace(/\/index\.html$/,'/');
  return path.endsWith('/')?path:path+'/';
 } catch {return '/';}
};
const current=normalize(location.pathname);
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function anchor(href,label,isCurrent){
 const a=el('a','ra-link',label);
 a.href=href;
 if(isCurrent){a.classList.add('ra-current');a.setAttribute('aria-current','page');}
 return a;
}
fetch(ENDPOINT,{cache:'no-cache',credentials:'same-origin'})
 .then(r=>{if(!r.ok)throw Error('navigation map HTTP '+r.status);return r.json();})
 .then(map=>{
 if(!map||map.version!==2||typeof map.pages!=='object')throw Error('invalid navigation map');
 const pages=map.pages,known=Object.prototype.hasOwnProperty.call(pages,current)?current:'/';
 const trail=[],seen=new Set();
 for(let u=known;u && pages[u] && !seen.has(u);u=pages[u].parent){seen.add(u);trail.unshift(u);}
 if(!trail.includes('/'))trail.unshift('/');
 const childMap={};
 for(const [url,item] of Object.entries(pages)){
  if(!item.visible)continue;
  const par=item.parent??'';
  (childMap[par]??=[]).push(url);
 }
 const priority=['/','/project/','/products/','/education/','/principles/','/recognition/','/os/','/guide/','/releases/','/source/','/trust/','/privacy/','/terms/','/license/'];
 const sort=(a,b)=>{
  const ia=priority.indexOf(a),ib=priority.indexOf(b);
  return (ia<0?999:ia)-(ib<0?999:ib)||pages[a].title.localeCompare(pages[b].title,'ja');
 };
 const sidebar=el('aside','ra-sidebar');
 sidebar.id='ra-sidebar';sidebar.setAttribute('aria-label','ページ一覧');
 const header=el('div','ra-sidebar-top');
 const heading=el('strong','ra-sidebar-title','ページを探す');
 const closeButton=el('button','ra-sidebar-close','閉じる ×');
 closeButton.type='button';closeButton.setAttribute('aria-label','ページ一覧を閉じる');
 header.append(heading,closeButton);sidebar.append(header);
 const nav=el('nav','ra-site-tree');nav.setAttribute('aria-label','ResoArc サイト階層');
 function draw(parent,host,depth){
  if(depth>9)return;
  for(const url of (childMap[parent]??[]).sort(sort)){
   const item=pages[url],kids=childMap[url]??[];
   const container=el('div','ra-node');
   const row=el('div','ra-node-row');
   const link=anchor(url,item.title,url===known);
   row.append(link);
   if(kids.length){
    const button=el('button','ra-expand',trail.includes(url)?'−':'+');
    button.type='button';
    button.setAttribute('aria-label',item.title+' の下位ページを開閉');
    button.setAttribute('aria-expanded',String(trail.includes(url)));
    const inner=el('div','ra-children');
    inner.hidden=!trail.includes(url);
    draw(url,inner,depth+1);
    button.addEventListener('click',()=>{
     inner.hidden=!inner.hidden;
     button.setAttribute('aria-expanded',String(!inner.hidden));
     button.textContent=inner.hidden?'+':'−';
    });
    row.append(button);container.append(row,inner);
   } else {container.append(row);}
   host.append(container);
  }
 }
 draw('',nav,0);sidebar.append(nav);
 const overlay=el('button','ra-overlay');
 overlay.type='button';overlay.setAttribute('aria-label','ページ一覧を閉じる');
 const crumb=el('nav','ra-breadcrumb');
 crumb.setAttribute('aria-label','パンくずリスト');
 const toggle=el('button','ra-nav-toggle','☰ ページ一覧');
 toggle.type='button';
 toggle.setAttribute('aria-controls','ra-sidebar');
 toggle.setAttribute('aria-expanded','false');
 crumb.append(toggle);
 const trailLabel=el('div','ra-crumb-items');
 for(let i=0;i<trail.length;i++){
  const url=trail[i],item=pages[url];
  if(i){const sep=el('span','ra-sep','›');sep.setAttribute('aria-hidden','true');trailLabel.append(sep);}
  if(i===trail.length-1){
   const span=el('span','ra-crumb-current',url===known?item.title:document.title);
   span.setAttribute('aria-current','page');trailLabel.append(span);
  } else {trailLabel.append(anchor(url,item.title,false));}
 }
 crumb.append(trailLabel);
 const desktop=window.matchMedia('(min-width: 960px)');
 const expanded=()=>desktop.matches?!document.body.classList.contains('ra-sidebar-hidden'):document.body.classList.contains('ra-drawer-open');
 const syncExpanded=()=>toggle.setAttribute('aria-expanded',String(expanded()));
 const close=()=>{
  document.body.classList.remove('ra-drawer-open');
  syncExpanded();
 };
 const open=()=>{
  document.body.classList.add('ra-drawer-open');
  syncExpanded();
  closeButton.focus();
 };
 toggle.addEventListener('click',()=>{
  if(desktop.matches){
   document.body.classList.toggle('ra-sidebar-hidden');
   syncExpanded();
  }else{
   document.body.classList.contains('ra-drawer-open')?close():open();
  }
 });
 closeButton.addEventListener('click',()=>{close();toggle.focus();});
 overlay.addEventListener('click',()=>{close();toggle.focus();});
 document.addEventListener('keydown',evt=>{
  if(evt.key==='Escape'&&document.body.classList.contains('ra-drawer-open')){close();toggle.focus();}
 });
 sidebar.addEventListener('click',evt=>{
  if(evt.target.closest('a')&&window.matchMedia('(max-width: 959px)').matches)close();
 });
 const restore=()=>{
  document.body.classList.remove('ra-drawer-open');
  syncExpanded();
 };
 desktop.addEventListener?.('change',restore);
 const siteHeader=document.querySelector('header.site-header');
 const main=document.querySelector('main');
 if(!siteHeader||!main)throw Error('Missing site header or main for navigation');
 document.body.append(sidebar,overlay);
 // Both controls and breadcrumb belong to the persistent site header, not the scrollable main.
 siteHeader.append(crumb);
 const updateHeight=()=>document.documentElement.style.setProperty(
  '--ra-nav-head-height',Math.ceil(siteHeader.getBoundingClientRect().height)+'px');
 updateHeight();
 if(typeof ResizeObserver!=='undefined'){
  const observer=new ResizeObserver(updateHeight);
  observer.observe(siteHeader);
 }else window.addEventListener('resize',updateHeight,{passive:true});
 syncExpanded();
 document.body.classList.add('ra-nav-ready');
 }).catch(error=>console.warn('ResoArc navigation unavailable:',error));
})();
