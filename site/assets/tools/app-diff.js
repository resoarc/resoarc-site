/* ResoArc: kintone app settings JSON diff v0.1, MIT. Local-only, no fetch. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const files=[$('diff-before'),$('diff-after')], btn=$('diff-run'), status=$('diff-status');
const result=$('diff-result'), summary=$('diff-summary'), body=$('diff-body');
const limit=5*1024*1024, maxShown=300;
const secret=/(token|password|secret|credential|api.?key|private.?key|authorization)/i;
const accepted=(f)=>f && f.size<=limit;
function update(){btn.disabled=!files.every(x=>accepted(x.files[0]));}
files.forEach(x=>x.addEventListener('change',()=>{result.hidden=true;update();}));
function jsonType(o){return Array.isArray(o)?'array':o===null?'null':typeof o;}
function secureValue(value,key){
 if(secret.test(key))return '[MASKED]';
 if(value===undefined)return '（なし）';
 const s=JSON.stringify(value);
 return s===undefined?String(value):s.length>250?s.slice(0,250)+'…':s;
}
function traverse(a,b,path,changes,depth){
 if(changes.length>5000)throw Error('差分が5,000件を超えたため中止しました。');
 if(depth>60)throw Error('JSONが深すぎるため比較できません。');
 if(JSON.stringify(a)===JSON.stringify(b) && jsonType(a)!=='object')return;
 const aa=jsonType(a),bb=jsonType(b);
 if((aa==='object'&&bb==='object')||(aa==='array'&&bb==='array')){
   const keys=new Set([...Object.keys(a),...Object.keys(b)]);
   for(const key of [...keys].sort((x,y)=>x.localeCompare(y,'ja'))){
     if(!Object.prototype.hasOwnProperty.call(a,key))changes.push({type:'追加',path:[...path,key],old:undefined,new:b[key]});
     else if(!Object.prototype.hasOwnProperty.call(b,key))changes.push({type:'削除',path:[...path,key],old:a[key],new:undefined});
     else traverse(a[key],b[key],[...path,key],changes,depth+1);
   }
   return;
 }
 if(a!==b)changes.push({type:'変更',path,old:a,new:b});
}
function safeCell(row,tag,value){
 const el=document.createElement(tag);el.textContent=value;row.appendChild(el);
}
btn.addEventListener('click',async()=>{
 btn.disabled=true;result.hidden=true;status.textContent='比較中…';
 try{
   const [before,after]=await Promise.all(files.map(async x=>{
     const f=x.files[0];if(!accepted(f))throw Error('各ファイルは5 MiB以下にしてください。');
     return JSON.parse(await f.text());
   }));
   const diffs=[];traverse(before,after,[],diffs,0);
   body.replaceChildren();
   let adds=0,deletes=0,updates=0;
   for(const item of diffs){
     if(item.type==='追加')adds++;else if(item.type==='削除')deletes++;else updates++;
   }
   summary.textContent='追加 '+adds+'件 ／ 削除 '+deletes+'件 ／ 変更 '+updates+'件（計 '+diffs.length+'件）';
   for(const d of diffs.slice(0,maxShown)){
     const row=document.createElement('tr');
     const key=d.path.join('.');
     safeCell(row,'td',d.type);
     safeCell(row,'td',key||'（ルート）');
     safeCell(row,'td',secureValue(d.old,key));
     safeCell(row,'td',secureValue(d.new,key));
     body.appendChild(row);
   }
   if(diffs.length>maxShown){
     const row=document.createElement('tr');const cell=document.createElement('td');cell.colSpan=4;
     cell.textContent='表示上限300件を超えたため残りの差分は省略しました。';row.appendChild(cell);body.appendChild(row);
   }
   result.hidden=false;
   status.textContent='比較完了。JSONデータを外部へ送信していません。';
 }catch(err){status.textContent='比較できませんでした：'+(err.message||err);}
 finally{update();}
});
update();
})();
