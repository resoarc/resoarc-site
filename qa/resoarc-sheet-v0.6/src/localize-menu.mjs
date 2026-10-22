// Visual Japanese labels for FortuneSheet's transient English context menu.
// Preserve the vendor's DOM text and event listeners: we only add attributes.
const TEXT = Object.freeze({
  'Copy':'コピー','Paste':'貼り付け','Cut':'切り取り',
  'Insert Row Above':'上に行を挿入','Insert Row Below':'下に行を挿入',
  'Insert Column Left':'左に列を挿入','Insert Column Right':'右に列を挿入',
  'Clear content':'内容をクリア','Sort':'並べ替え',
  'Ascending sort':'昇順で並べ替え','Descending sort':'降順で並べ替え',
  'Filter':'フィルター','Insert image':'画像を挿入','Insert link':'リンクを挿入',
  'Delete Row':'行を削除','Delete Column':'列を削除',
  'Merge cells':'セルを結合','Unmerge cells':'結合を解除',
  'Hide Row':'行を非表示','Hide Column':'列を非表示',
  'Insert comment':'コメントを挿入','Delete comment':'コメントを削除'
});
function translateMenus(root){
  for(const menu of root.querySelectorAll('.fortune-context-menu')){
    for(const item of menu.querySelectorAll('.luckysheet-cols-menuitem')){
      const text=(item.textContent||'').replace(/\s+/g,' ').trim();
      const japanese=TEXT[text];
      if(japanese && item.dataset.resoarcLabel!==japanese){
        item.dataset.resoarcLabel=japanese;
        item.setAttribute('aria-label',japanese);
        item.setAttribute('title',japanese);
      }
    }
    for(const input of menu.querySelectorAll('input[placeholder="Number"]'))
      input.setAttribute('aria-label','挿入数');
  }
}
export function setupJapaneseContextMenus(root=document){
  let scheduled=false;
  function update(){scheduled=false;translateMenus(root);}
  const observer=new MutationObserver(()=>{
    if(!scheduled){scheduled=true;queueMicrotask(update);}
  });
  observer.observe(root.body||root,{childList:true,subtree:true});
  update();
  return ()=>observer.disconnect();
}
