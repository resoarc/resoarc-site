/* ResoArc navigation: grouped by purpose. Sitemap remains the canonical page source. */
(()=>{'use strict';
const endpoint='/assets/navigation-map.json';
const normalize=raw=>{
 try {const u=new URL(raw,location.origin);const p=u.pathname.replace(/\/index\.html$/,'/');return p.endsWith('/')?p:p+'/';}
 catch{return '/';}
};
const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
const anchor=(url,label,current)=>{const a=el('a','ra-link',label);a.href=url;if(current){a.classList.add('ra-current');a.setAttribute('aria-current','page');}return a;};
fetch(endpoint,{cache:'no-cache',credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('navigation map HTTP '+r.status);return r.json();}).then(map=>{
 if(!map||map.version!==2||typeof map.pages!=='object')throw Error('invalid navigation map');
 const pages=map.pages;
 const current=normalize(location.pathname);
 const known=Object.prototype.hasOwnProperty.call(pages,current)?current:'/';
 const trail=[],seen=new Set();
 for(let u=known;u&&pages[u]&&!seen.has(u);u=pages[u].parent){seen.add(u);trail.unshift(u);}
 if(!trail.includes('/'))trail.unshift('/');
 const headerSection=trail.find(u=>u!=='/'&&['/project/','/products/','/principles/','/recognition/','/os/'].includes(u))||(known==='/'?'/':null);
 document.querySelectorAll('header.site-header .desktop-nav a, header.site-header .mobile-panel a').forEach(a=>{
  a.classList.remove('is-active');a.removeAttribute('aria-current');
  if(headerSection&&normalize(a.getAttribute('href')||'')===headerSection){
   a.classList.add('is-active');a.setAttribute('aria-current',current===headerSection?'page':'location');
  }
 });
 // Presentation categories never replace real URLs or breadcrumbs.
 const navPages={};
 for(const [url,item] of Object.entries(pages)){if(item.visible)navPages[url]={...item};}
 function subgroup(id,title,parent,urls){
  const children=urls.filter(url=>navPages[url]);
  if(!children.length)return;
  navPages[id]={title,parent,visible:true,virtual:true};
  for(const url of children)navPages[url].parent=id;
 }
 subgroup('@k-input','入力・編集','/products/kintone/',[
  '/products/kintone/postal-address/','/products/kintone/input-template/','/products/kintone/reuse-reset/',
  '/products/kintone/text-normalizer/','/products/kintone/field-help/','/products/kintone/lookup-suggest/',
  '/products/kintone/mail-compose/']);
 subgroup('@k-data','一覧・集計','/products/kintone/',[
  '/products/kintone/csv-export/','/products/kintone/list-aggregate/','/products/kintone/attachment-count/']);
 subgroup('@k-view','表示・画面移動','/products/kintone/',[
  '/products/kintone/tabs/','/products/kintone/record-toc/','/products/kintone/save-navigation/',
  '/products/kintone/related-links/','/products/kintone/qr-code/']);
 subgroup('@k-manage','管理・自動化','/products/kintone/',['/tools/kintone-auto-number/']);
 subgroup('@w-files','ファイル・データ検査','/products/web/',[
  '/tools/hash/','/tools/csv/','/tools/kintone-app-diff/',
  '/tools/kintone-import-check/','/tools/kintone-bulk-preview/']);
 subgroup('@w-audit','設定・整合性診断','/products/web/',[
  '/tools/kintone-permission-audit/','/tools/kintone-duplicates/','/tools/kintone-lookup-audit/']);
 subgroup('@w-report','集計・帳票','/products/web/',[
  '/tools/kintone-cross-aggregate/','/tools/kintone-print-report/']);
 subgroup('@development','ベータ・開発中','/products/',[
  '/products/web/qaiuick/','/products/development-status/','/products/roadmap/',
  '/products/backup-migration/','/tools/qaiuick-budget/','/tools/qaiuick-customers/',
  '/tools/qaiuick-demo/','/tools/qaiuick-inventory/','/tools/qaiuick-spec-inventory/',
  '/tools/qaiuick-spec-tickets/','/tools/qaiuick-tickets/']);
 const childMap={};
 for(const [url,item] of Object.entries(navPages)){
  if(url==='/')continue;
  (childMap[item.parent||'']??=[]).push(url);
 }
 const order=[
  '/products/kintone/','/products/web/','/products/sheet/','@development',
  '@k-input','@k-data','@k-view','@k-manage','/products/kintone/release-integrity/',
  '@w-files','@w-audit','@w-report','/products/web/screens/',
  '/products/web/qaiuick/','/products/development-status/','/products/roadmap/'
 ];
 const sort=(a,b)=>{
  const ia=order.indexOf(a),ib=order.indexOf(b);
  return (ia<0?999:ia)-(ib<0?999:ib)||(navPages[a]?.title||'').localeCompare(navPages[b]?.title||'','ja');
 };
 const displayTrail=[],seenDisplay=new Set();
 for(let u=known;u&&navPages[u]&&!seenDisplay.has(u);u=navPages[u].parent){seenDisplay.add(u);displayTrail.unshift(u);}
 const sections=[
  {title:'無料アプリ・ツール',subtitle:'使うものを探す',roots:['/','/products/','/os/']},
  {title:'使い方・学習',subtitle:'導入と教材',roots:['/guide/','/education/']},
  {title:'ResoArcの活動',subtitle:'概要・実績・更新',roots:['/project/','/community/','/recognition/','/releases/']},
  {title:'品質・公開情報',subtitle:'根拠・運用・安全',roots:['/principles/','/trust/','/source/','/security/','/status/']},
  {title:'利用条件・その他',subtitle:'ポリシーと言語',roots:['/privacy/','/terms/','/license/','/en/']}
 ];
 const sidebar=el('aside','ra-sidebar');
 sidebar.id='ra-sidebar';sidebar.setAttribute('aria-label','ページ一覧');
 const top=el('div','ra-sidebar-top');
 const title=el('strong','ra-sidebar-title','目的から探す');
 const closeButton=el('button','ra-sidebar-close','閉じる ×');
 closeButton.type='button';closeButton.setAttribute('aria-label','ページ一覧を閉じる');
 top.append(title,closeButton);sidebar.append(top);
 const search=el('input','ra-sidebar-search');
 search.type='search';search.placeholder='ページ・製品を検索';
 search.setAttribute('aria-label','ページや製品名で検索');search.autocomplete='off';sidebar.append(search);
 const nav=el('nav','ra-site-tree');nav.setAttribute('aria-label','ResoArc サイト階層');
 function drawRoute(url,host,depth){
  if(depth>8||!navPages[url])return;
  const item=navPages[url],kids=url==='/'?[]:(childMap[url]||[]).sort(sort);
  const node=el('div','ra-node'+(item.virtual?' ra-virtual':''));
  node.dataset.navUrl=url;
  const row=el('div','ra-node-row');
  const expanded=displayTrail.includes(url);
  const inner=kids.length?el('div','ra-children'):null;
  if(item.virtual){
   const btn=el('button','ra-category-toggle',item.title+' ('+kids.length+')');
   btn.type='button';btn.setAttribute('aria-expanded',String(expanded));
   btn.setAttribute('aria-label',item.title+' の製品を開閉');
   row.append(btn);
   if(inner){
    inner.hidden=!expanded;
    btn.addEventListener('click',()=>{inner.hidden=!inner.hidden;btn.setAttribute('aria-expanded',String(!inner.hidden));});
   }
  }else{
   row.append(anchor(url,item.title,url===known));
   if(kids.length){
    const btn=el('button','ra-expand',expanded?'−':'+');
    btn.type='button';btn.setAttribute('aria-label',item.title+' の下位ページを開閉');
    btn.setAttribute('aria-expanded',String(expanded));
    btn.addEventListener('click',()=>{
     inner.hidden=!inner.hidden;
     btn.setAttribute('aria-expanded',String(!inner.hidden));
     btn.textContent=inner.hidden?'+':'−';
    });
    row.append(btn);inner.hidden=!expanded;
   }
  }
  node.append(row);
  if(inner){for(const child of kids)drawRoute(child,inner,depth+1);node.append(inner);}
  host.append(node);
 }
 const groups=[];
 for(const [index,def] of sections.entries()){
  const group=el('details','ra-menu-group');
  const active=def.roots.some(url=>displayTrail.includes(url));
  group.open=active||(known==='/'&&index===0);
  const summary=el('summary','ra-menu-heading');
  const label=el('span','ra-menu-main',def.title);
  const sub=el('small','ra-menu-sub',def.subtitle);
  summary.append(label,sub);group.append(summary);
  const body=el('div','ra-menu-body');
  for(const url of def.roots){drawRoute(url,body,0);}
  group.append(body);nav.append(group);groups.push(group);
 }
 sidebar.append(nav);
 // A search reveals matching descendants and opens the necessary parent groups.
 const nodes=[...nav.querySelectorAll('.ra-node')];
 const expandedSnapshot=()=>new Map(nodes.map(n=>{
  const btn=n.querySelector(':scope > .ra-node-row [aria-expanded]');
  return [n,btn?.getAttribute('aria-expanded')==='true'];
 }));
 let beforeSearch=null,beforeGroups=null;
 const updateNode=(node,expanded)=>{
  const inner=node.querySelector(':scope > .ra-children');
  const btn=node.querySelector(':scope > .ra-node-row [aria-expanded]');
  if(inner)inner.hidden=!expanded;
  if(btn){btn.setAttribute('aria-expanded',String(expanded));if(btn.classList.contains('ra-expand'))btn.textContent=expanded?'−':'+';}
 };
 search.addEventListener('input',()=>{
  const term=search.value.trim().toLocaleLowerCase('ja');
  if(!term){
   for(const group of groups)group.hidden=false;
   for(const node of nodes){node.hidden=false;updateNode(node,beforeSearch?.get(node)??(displayTrail.includes(node.dataset.navUrl)));}
   if(beforeGroups)groups.forEach((g,i)=>{g.open=beforeGroups[i];});
   beforeSearch=null;beforeGroups=null;return;
  }
  if(!beforeSearch){beforeSearch=expandedSnapshot();beforeGroups=groups.map(g=>g.open);}
  for(const node of [...nodes].reverse()){
   const row=node.querySelector(':scope > .ra-node-row');
   const label=row?.querySelector('.ra-link,.ra-category-toggle')?.textContent||'';
   const inner=node.querySelector(':scope > .ra-children');
   const descendants=inner?[...inner.children].some(child=>!child.hidden):false;
   node.hidden=!(label.toLocaleLowerCase('ja').includes(term)||descendants);
   if(descendants)updateNode(node,true);
  }
  groups.forEach(group=>{
   const match=group.querySelector('.ra-menu-main')?.textContent.toLocaleLowerCase('ja').includes(term);
   const any=[...group.querySelectorAll(':scope > .ra-menu-body > .ra-node')].some(node=>!node.hidden);
   group.hidden=!match&&!any;
   if(match||any)group.open=true;
  });
 });
 const overlay=el('button','ra-overlay');
 overlay.type='button';overlay.setAttribute('aria-label','ページ一覧を閉じる');
 const crumb=el('nav','ra-breadcrumb');crumb.setAttribute('aria-label','パンくずリスト');
 const toggle=el('button','ra-nav-toggle','☰ ページ一覧');toggle.type='button';
 toggle.setAttribute('aria-controls','ra-sidebar');toggle.setAttribute('aria-expanded','false');
 crumb.append(toggle);
 const crumbs=el('div','ra-crumb-items');
 for(let i=0;i<trail.length;i++){
  const url=trail[i],item=pages[url];
  if(i){const sep=el('span','ra-sep','›');sep.setAttribute('aria-hidden','true');crumbs.append(sep);}
  if(i===trail.length-1){
   const node=el('span','ra-crumb-current',url===known?item.title:document.title);
   node.setAttribute('aria-current','page');crumbs.append(node);
  }else{crumbs.append(anchor(url,item.title,false));}
 }
 crumb.append(crumbs);
 const desktop=window.matchMedia('(min-width: 960px)');
 const expanded=()=>desktop.matches?!document.body.classList.contains('ra-sidebar-hidden'):document.body.classList.contains('ra-drawer-open');
 const sync=()=>toggle.setAttribute('aria-expanded',String(expanded()));
 const close=()=>{document.body.classList.remove('ra-drawer-open');sync();};
 const open=()=>{document.body.classList.add('ra-drawer-open');sync();closeButton.focus();};
 toggle.addEventListener('click',()=>{if(desktop.matches){document.body.classList.toggle('ra-sidebar-hidden');sync();}else{document.body.classList.contains('ra-drawer-open')?close():open();}});
 closeButton.addEventListener('click',()=>{close();toggle.focus();});
 overlay.addEventListener('click',()=>{close();toggle.focus();});
 document.addEventListener('keydown',evt=>{if(evt.key==='Escape'&&document.body.classList.contains('ra-drawer-open')){close();toggle.focus();}});
 sidebar.addEventListener('click',evt=>{if(evt.target.closest('a')&&window.matchMedia('(max-width: 959px)').matches)close();});
 desktop.addEventListener?.('change',()=>{document.body.classList.remove('ra-drawer-open');sync();});
 const header=document.querySelector('header.site-header');
 const main=document.querySelector('main');
 if(!header||!main)throw Error('Missing site header or main for navigation');
 document.body.append(sidebar,overlay);header.append(crumb);
 const updateHeight=()=>document.documentElement.style.setProperty('--ra-nav-head-height',Math.ceil(header.getBoundingClientRect().height)+'px');
 updateHeight();
 if(typeof ResizeObserver!=='undefined'){new ResizeObserver(updateHeight).observe(header);}
 else{window.addEventListener('resize',updateHeight,{passive:true});}
 sync();document.body.classList.add('ra-nav-ready');
}).catch(e=>console.warn('ResoArc navigation unavailable:',e));
})();
