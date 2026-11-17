// UI-independent, bounded table helpers. No workbook mutation here.
export function displayValue(cell) {
 if (cell == null) return '';
 const value = cell?.v;
 const raw = value && typeof value === 'object' ? (value.m ?? value.v ?? '') : (value ?? '');
 return raw == null ? '' : String(raw);
}
export function isFormula(cell) { return typeof cell?.f === 'string' && cell.f.length > 0; }
export function isMerged(sheet) { return Object.keys(sheet?.config?.merge || {}).length > 0; }
export function isSheetProtected(sheet) {
 return Boolean(sheet?.config?.protect || sheet?.protect || sheet?.isProtected);
}
export function assertSheetEditable(sheet) {
 if(!sheet)throw Error('操作対象のシートを取得できません。');
 if(isSheetProtected(sheet))throw Error('保護されたシートでは編集できません。保護を解除してから操作してください。');
}

export function usedRows(sheet) {
 const data = Array.isArray(sheet?.data) ? sheet.data : [];
 for(let r=data.length-1;r>=0;r--) {
  if(Array.isArray(data[r]) && data[r].some(c=>c != null && (isFormula(c)||displayValue(c)!=='')))return r+1;
 }
 return 0;
}
export function findCells(sheet, term, {caseSensitive=false, limit=1000}={}) {
 if(!term || typeof term !== 'string')return [];
 const needle=caseSensitive?term:term.toLocaleLowerCase('ja');
 const hits=[],data=sheet?.data||[];
 for(let r=0;r<Math.min(data.length,100000);r++){
  const row=data[r]||[];
  for(let c=0;c<Math.min(row.length,1000);c++){
   const cell=row[c];
   const raw=displayValue(cell);
   if(raw && (caseSensitive?raw:raw.toLocaleLowerCase('ja')).includes(needle)){
    hits.push({r,c,text:raw,formula:isFormula(cell)});
    if(hits.length>=limit)return hits;
   }
  }
 }
 return hits;
}
export function literalReplace(cell,term,replacement,{caseSensitive=false}={}) {
 if(typeof term!=='string'||!term)throw Error('検索文字列を入力してください。');
 if(isFormula(cell))return null;
 const scalar=cell?.v && typeof cell.v==='object' ? cell.v.v : cell?.v;
 if(typeof scalar!=='string')return null;
 // RegExp matching maintains offsets in the original string. Case folding
 // with toLocaleLowerCase() can expand Unicode code points and corrupt slices.
 const escaped=term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 const pattern=new RegExp(escaped,caseSensitive?'gu':'giu');
 if(!pattern.test(scalar))return null;
 return scalar.replace(new RegExp(escaped,caseSensitive?'gu':'giu'),()=>replacement);
}
// FortuneSheet uses empty objects/arrays as defaults for these features.
// Only populated feature metadata should block safe, whole-row sorting.
const populated=feature=>Array.isArray(feature)?feature.length>0:
 feature && typeof feature==='object'?Object.keys(feature).length>0:Boolean(feature);
export function isPlainSortable(sheet){
 if(!Array.isArray(sheet?.data))return false;
 if(isSheetProtected(sheet) || isMerged(sheet) || sheet?.isPivotTable) return false;
 if(['filter','filter_select','dataVerification','hyperlink','conditionformat','chart'].some(k=>populated(sheet[k])))return false;
 if(['rowhidden','rowlen'].some(k=>populated(sheet?.config?.[k])))return false;
 if(sheet.data.some(row=>(row||[]).some(isFormula)))return false;
 return true;
}
export function sortedSheet(sheet,column,direction='asc'){
 if(!isPlainSortable(sheet))throw Error('数式・結合・フィルター等のあるシートは、行を安全に移動できないため並べ替えできません。');
 if(!Number.isInteger(column)||column<0||column>999)throw Error('列番号が不正です。');
 if(direction!=='asc'&&direction!=='desc')throw Error('並べ替えの方向が不正です。');
 const n=usedRows(sheet);
 if(n<3)return {...sheet,data:sheet.data.map(row=>Array.isArray(row)?[...row]:row)};
 const values=sheet.data.slice(1,n).map((row,i)=>({row:Array.isArray(row)?[...row]:[],i}));
 const collator=new Intl.Collator('ja',{numeric:true,sensitivity:'base'});
 values.sort((a,b)=>{
  const va=a.row[column]?.v?.v ?? a.row[column]?.v ?? '';
  const vb=b.row[column]?.v?.v ?? b.row[column]?.v ?? '';
  const aEmpty=va===null||va===undefined||va==='', bEmpty=vb===null||vb===undefined||vb==='';
  if(aEmpty!==bEmpty)return aEmpty?1:-1;
  const cmp=typeof va==='number'&&typeof vb==='number'?va-vb:collator.compare(String(va),String(vb));
  return (direction==='asc'?cmp:-cmp)||a.i-b.i;
 });
 return {...sheet,data:[...sheet.data.slice(0,1),...values.map(x=>x.row),...sheet.data.slice(n)]};
}
export function rowsNotMatching(sheet,column,term){
 if(typeof term!=='string'||!term.trim())throw Error('絞り込む文字を入力してください。');
 const count=usedRows(sheet);
 if(count>5000)throw Error('フィルター対象が5,000行を超えています。');
 const needle=term.toLocaleLowerCase('ja');
 const hidden=[];
 for(let r=1;r<count;r++)if(!displayValue(sheet.data[r]?.[column]).toLocaleLowerCase('ja').includes(needle))hidden.push(String(r));
 return hidden;
}
// Excel and other spreadsheet programs may execute pasted TSV text as formulas.
// Escape only text-like values, never legitimate numeric cells or formulas' numeric results.
// A leading apostrophe tells Excel to keep the following text as text.
export function escapeClipboardFormula(value) {
 if(typeof value!=='string')return value;
 return /^[\u0000-\u0020\ufeff]*[=+\-@]/u.test(value)?"'"+value:value;
}
export function formatTsv(data){
 return data.map(row=>row.map(value=>{
  const s=String(value??'');
  return /[\t\r\n"]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
 }).join('\t')).join('\r\n');
}
