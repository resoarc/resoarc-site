/* Group published plugins by use case. Static product cards remain available without JavaScript. */
(()=>{'use strict';
 const root=document.querySelector('.kintone-catalog');
 if(!root)return;
 const host=root.querySelector('#kc-products');
 const cards=Array.from(root.querySelectorAll('.kc-product[data-category]'));
 const buttons=Array.from(root.querySelectorAll('.kc-filter-buttons button[data-category]'));
 const input=root.querySelector('#kc-search');
 const empty=root.querySelector('#kc-no-results');
 const count=root.querySelector('#kc-showing');
 if(!host||!cards.length||!input||!empty||!count)return;
 const sections=[
  {key:'入力・設定',title:'入力・編集',caption:'入力補助・表記ゆれ対策・ルックアップ'},
  {key:'一覧・データ',title:'一覧・集計',caption:'一覧表示・CSV出力・件数の把握'},
  {key:'表示・移動',title:'表示・画面移動',caption:'フォーム整理・画面移動・QRコード'},
  {key:'管理',title:'管理・自動化',caption:'採番など日常の運用を支援'}
 ];
 const groups=[];
 host.classList.remove('kc-product-grid');
 host.classList.add('kc-grouped-products');
 for(const def of sections){
  const matched=cards.filter(card=>card.dataset.category===def.key);
  if(!matched.length)continue;
  const section=document.createElement('section');
  section.className='kc-category-section';
  section.dataset.category=def.key;
  section.setAttribute('aria-label',def.title);
  const header=document.createElement('div');header.className='kc-category-heading';
  const heading=document.createElement('h3');heading.textContent=def.title;
  const number=document.createElement('span');number.className='kc-category-count';
  number.textContent=matched.length+'製品';
  const note=document.createElement('p');note.textContent=def.caption;
  header.append(heading,number,note);section.append(header);
  const grid=document.createElement('div');grid.className='kc-product-grid';
  for(const card of matched)grid.append(card);
  section.append(grid);host.append(section);
  groups.push({section,matched,number});
 }
 let current='すべて';
 const apply=()=>{
  const word=input.value.trim().toLocaleLowerCase('ja');
  let visible=0;
  for(const group of groups){
   let inGroup=0;
   for(const card of group.matched){
    const matches=(current==='すべて'||card.dataset.category===current)
      &&(!word||(card.dataset.search||'').toLocaleLowerCase('ja').includes(word));
    card.hidden=!matches;
    if(matches)inGroup++;
   }
   group.section.hidden=inGroup===0;
   group.number.textContent=inGroup+'製品';
   visible+=inGroup;
  }
  for(const btn of buttons)btn.setAttribute('aria-pressed',String(btn.dataset.category===current));
  count.textContent=visible+' 製品を表示';
  empty.hidden=visible!==0;
 };
 for(const button of buttons)button.addEventListener('click',()=>{current=button.dataset.category;apply();});
 input.addEventListener('input',apply);
 root.classList.add('kc-ready');apply();
})();