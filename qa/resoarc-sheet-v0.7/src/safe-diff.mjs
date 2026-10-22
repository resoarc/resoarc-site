// Canonical FortuneSheet snapshot for non-destructive, value-only edits.
// It is intentionally independent from the mutable data returned by getAllSheets().
const IGNORED_CELL_KEYS=new Set(['v','f','m','ct','vt','qp','tb','rc','mc']);
const sortedObject=obj=>Object.fromEntries(Object.entries(obj||{}).sort(([a],[b])=>a.localeCompare(b)));
function cellMeta(cell){
 const extra=Object.fromEntries(Object.entries(cell||{}).filter(([k])=>!IGNORED_CELL_KEYS.has(k)));
 const ct={...(cell?.ct||{})}; delete ct.t; if(ct.fa==='General')delete ct.fa; if(!Object.keys(ct).length)delete extra.ct;else extra.ct=ct;
 return JSON.stringify(sortedObject(extra));
}
function semantic(cell){
 if(!cell||typeof cell!=='object')return {type:'blank',value:null,formula:null};
 const formula=typeof cell.f==='string'&&cell.f.trim()?cell.f.replace(/^=/,''):null;
 if(formula)return {type:'formula',value:null,formula};
 let raw=cell.v;
 if(raw==null||raw==='')return {type:'blank',value:null,formula:null};
 const hint=cell.ct?.t;
 if(hint==='e')return {type:'error',value:String(raw),formula:null};
 if(hint==='b'||typeof raw==='boolean')return {type:'boolean',value:raw===true||raw===1||raw==='1'||raw==='TRUE',formula:null};
 if(typeof raw==='number'||(hint==='n'&&typeof raw==='string'&&raw.trim()!==''&&!Number.isNaN(Number(raw)))){
  const val=Number(raw);
  if(Number.isFinite(val))return {type:'number',value:val,formula:null};
 }
 return {type:'string',value:String(raw),formula:null};
}
function getSheetCells(sheet){
 const m=new Map();
 if(Array.isArray(sheet.data))sheet.data.forEach((row,r)=>{if(Array.isArray(row))row.forEach((cell,c)=>{if(cell!=null)m.set(r+','+c,{r,c,sem:semantic(cell),meta:cellMeta(cell)});});});
 else if(Array.isArray(sheet.celldata))for(const entry of sheet.celldata){if(entry?.v!=null)m.set(entry.r+','+entry.c,{r:entry.r,c:entry.c,sem:semantic(entry.v),meta:cellMeta(entry.v)});}
 return m;
}
function sheetMeta(s){
 return JSON.stringify({
  name:s.name,id:s.id,order:String(s.order??''),hide:s.hide??0,
  config:s.config||{},dataVerification:s.dataVerification||{},hyperlink:s.hyperlink||{},
  showGridLines:s.showGridLines,zoomRatio:s.zoomRatio,
  defaultColWidth:s.defaultColWidth,defaultRowHeight:s.defaultRowHeight,
 });
}
export function captureSnapshot(sheets){
 if(!Array.isArray(sheets)||!sheets.length)throw Error('ワークブックを取得できません。');
 return sheets.map(s=>({name:s.name,meta:sheetMeta(s),cells:getSheetCells(s)}));
}
export function valueOnlyDiff(before,after,maxEdits=500){
 const now=captureSnapshot(after);
 if(before.length!==now.length||before.some((s,i)=>s.name!==now[i].name))
  throw Error('シートの追加・削除・名前変更は安全保存では対応できません。通常のXLSX保存を選択してください。');
 const changes=[];
 for(let i=0;i<before.length;i++){
  const old=before[i],fresh=now[i];
  if(old.meta!==fresh.meta)throw Error('シート構造・列幅・設定が変更されています。安全保存はセル値のみ対応です。');
  const keys=new Set([...old.cells.keys(),...fresh.cells.keys()]);
  for(const k of keys){
   const prev=old.cells.get(k),next=fresh.cells.get(k);
   if((prev?.meta||'{}')!==(next?.meta||'{}'))
    throw Error('セルの書式が変更されています（'+old.name+' '+k+'）。安全保存では書式変更を扱えません。');
   const x=prev?.sem||{type:'blank',value:null,formula:null};
   const y=next?.sem||{type:'blank',value:null,formula:null};
   if(JSON.stringify(x)===JSON.stringify(y))continue;
   if(!prev||!next)throw Error('セルの追加・削除は安全保存の対象外です（'+old.name+' '+k+'）。');
   if(x.type==='formula'&&y.type!=='formula'||x.type!=='formula'&&y.type==='formula')
    throw Error('数式セルと通常セルの相互変更は安全保存の対象外です（'+old.name+' '+k+'）。');
   if(y.type==='error')throw Error('エラーセルは安全保存できません（'+old.name+' '+k+'）。');
   changes.push({sheet:old.name,r:next.r,c:next.c,before:x,after:y});
   if(changes.length>maxEdits)throw Error('安全保存は一度に'+maxEdits+'セルまでです。');
  }
 }
 return changes;
}
