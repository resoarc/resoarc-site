/* Only published product cards exist in DOM. Static fallback works without JS. */
(() => {
 const root=document.querySelector('.kintone-catalog');
 if (!root) return;
 const cards=Array.from(root.querySelectorAll('.kc-product[data-category]'));
 const buttons=Array.from(root.querySelectorAll('.kc-filter-buttons button[data-category]'));
 const input=root.querySelector('#kc-search');
 const empty=root.querySelector('#kc-no-results');
 const count=root.querySelector('#kc-showing');
 if (!input || !empty || !count) return;
 let current='すべて';
 const apply=()=>{
   const word=input.value.trim().toLocaleLowerCase('ja');
   let visible=0;
   for(const card of cards){
     const matches=(current==='すべて'||card.dataset.category===current)
       &&(!word||(card.dataset.search||'').toLocaleLowerCase('ja').includes(word));
     card.hidden=!matches;
     if(matches) visible++;
   }
   for(const btn of buttons)btn.setAttribute('aria-pressed',String(btn.dataset.category===current));
   count.textContent=visible+' 製品を表示';
   empty.hidden=visible!==0;
 };
 for(const button of buttons)button.addEventListener('click',()=>{current=button.dataset.category;apply()});
 input.addEventListener('input',apply);
 root.classList.add('kc-ready');
 apply();
})();
