/* SPDX-FileCopyrightText: 2026 ResoArc contributors
 * SPDX-License-Identifier: MIT */
/* Use-case grouping for the browser-tool catalog; retains the unmodified static fallback. */
(()=>{'use strict';
 const main=document.querySelector('main');
 if(!main)return;
 const grids=[...main.querySelectorAll('.product-grid')].filter(grid=>grid.querySelector('article.product-card'));
 if(!grids.length)return;
 const cards=grids.flatMap(grid=>[...grid.querySelectorAll(':scope > article.product-card')]);
 if(cards.length<8)return;
 const defs=[
  {title:'ファイル・データを検査する',caption:'CSV・差分・更新予定データを安全に確認',paths:[
   '/tools/hash/','/tools/csv/','/tools/kintone-app-diff/',
   '/tools/kintone-import-check/','/tools/kintone-bulk-preview/']},
  {title:'kintoneの設定を点検する',caption:'権限・重複・ルックアップの確認',paths:[
   '/tools/kintone-permission-audit/','/tools/kintone-duplicates/','/tools/kintone-lookup-audit/']},
  {title:'集計・帳票を作る',caption:'アプリ横断集計とPDF保存',paths:[
   '/tools/kintone-cross-aggregate/','/tools/kintone-print-report/']},
  {title:'アプリ開発を試す',caption:'開発フレームワークのβ版',paths:['/products/web/qaiuick/']}
 ];
 const urlOf=card=>card.querySelector('a[href^="/tools/"],a[href^="/products/web/qaiuick/"]')?.getAttribute('href')||'';
 const byUrl=new Map(cards.map(card=>[urlOf(card),card]));
 const wrapper=document.createElement('div');
 wrapper.className='ra-web-groups';
 wrapper.setAttribute('aria-label','Webツールを用途で探す');
 for(const def of defs){
  const found=def.paths.map(path=>byUrl.get(path)).filter(Boolean);
  if(!found.length)continue;
  const section=document.createElement('section');section.className='ra-web-group';
  const heading=document.createElement('div');heading.className='ra-web-group-heading';
  const title=document.createElement('h2');title.textContent=def.title;
  const count=document.createElement('span');count.className='ra-web-group-count';count.textContent=found.length+'件';
  const caption=document.createElement('p');caption.textContent=def.caption;
  heading.append(title,count,caption);section.append(heading);
  const grid=document.createElement('div');grid.className='product-grid';
  for(const card of found){grid.append(card);byUrl.delete(urlOf(card));}
  section.append(grid);wrapper.append(section);
 }
 if(byUrl.size){
  const section=document.createElement('section');section.className='ra-web-group';
  const heading=document.createElement('h2');heading.textContent='その他のツール';section.append(heading);
  const grid=document.createElement('div');grid.className='product-grid';
  for(const card of byUrl.values())grid.append(card);
  section.append(grid);wrapper.append(section);
 }
 grids[0].replaceWith(wrapper);
 for(const grid of grids.slice(1))grid.remove();
})();
