import React,{useState,useRef,useEffect} from 'react';
import SheetToolsDialog from './SheetToolsDialog.jsx';
import {findCells,literalReplace,isMerged,assertSheetEditable,usedRows,sortedSheet,rowsNotMatching,formatTsv,escapeClipboardFormula} from './sheet-operations.mjs';
import {validatePaste} from './paste-values.mjs';
import {auditExcelSave} from './compat-audit.mjs';
import {transformFortuneToExcel} from '@corbe30/fortune-excel';
import {coordToA1} from './FormulaBar.jsx';
import './sheet-extras.css';

export default function SheetExtras({apiRef,selectedRef,explicitTargetRef,onPinTarget,sourceFile,features,onSelect,onPaste,onPasteFallback,onDirty,onUnsafeChange,onNotice,onLastAudit,onReplaceSheets,onFilterStateChange,onCanRestructure,busy}){
 const [dialog,setDialog]=useState(null),[audit,setAudit]=useState(null),[filterActive,setFilterActive]=useState(false),[working,setWorking]=useState(false);
 const hiddenRef=useRef([]);
 const filteredSheetId=useRef(null);
 const filterShapeRef=useRef(null);
 const assertFilterShape=()=>{
  const old=filterShapeRef.current;
  if(!old)return;
  const current=sheet();
  if(current.row!==old.row||current.column!==old.column||current.data.length!==old.dataLength)
   throw Error('フィルター後に行・列構造が変化しました。誤った行を再表示しないため解除を中止します。バックアップから復元してください。');
 };
 useEffect(()=>{
  const handler=e=>{
   if(!(e.ctrlKey||e.metaKey)||e.altKey||e.shiftKey||e.key.toLowerCase()!=='f')return;
   if(e.target instanceof Element && e.target.closest('input,textarea,select,[contenteditable="true"]'))return;
   if(document.querySelector('[role="dialog"][aria-modal="true"]'))return;
   e.preventDefault();e.stopPropagation();setDialog('search');
  };
  window.addEventListener('keydown',handler,true);
  return ()=>window.removeEventListener('keydown',handler,true);
 },[]);
 const currentFocus=()=>explicitTargetRef?.current||selectedRef.current;
 const api=()=>{if(!apiRef.current)throw Error('表計算エンジンが起動していません。');return apiRef.current;};
 const sheet=()=>{const s=api().getSheet?.();if(!s||!Array.isArray(s.data))throw Error('編集できるシートがありません。');return s;};
 const changed=(structural=false)=>{onDirty();onLastAudit(null);if(structural)onUnsafeChange();};
 const notify=(m)=>{onNotice(m);return m;};
 const guard=(fn)=>{try{return fn();}catch(e){return notify('操作できません: '+(e.message||String(e)));}};
 const jump=(r,c)=>{
  const sel={row:[r,r],column:[c,c]};
  api().scroll?.({targetRow:r,targetColumn:c});onSelect(sel);onPinTarget({r,c});
 };
 const findNext=(term)=>guard(()=>{
  if(!term)throw Error('検索する文字を入力してください。');
  const hits=findCells(sheet(),term,{limit:1001});
  if(!hits.length)return notify('一致するセルはありません。');
  const {r,c}=currentFocus();
  const h=hits.find(x=>x.r>r||(x.r===r&&x.c>c))||hits[0];
  jump(h.r,h.c);
  return notify(coordToA1(h.r,h.c)+' に移動しました（'+(hits.length>1000?'1,000件以上':hits.length+'件')+'）。');
 });
 const replace=(term,replacement,all)=>guard(()=>{
  if(!term)throw Error('検索文字列を入力してください。');
  const s=sheet();
  assertSheetEditable(s);
  if(isMerged(s))throw Error('結合セルのあるシートでは置換を実行できません。');
  const hits=findCells(s,term,{limit:501});
  if(all&&hits.length>500)throw Error('置換候補は500件までです。検索語を絞ってください。');
  const selection=currentFocus();
  const candidates=(all?hits:hits.filter(h=>h.r===selection.r&&h.c===selection.c))
   .map(h=>({...h,replacement:literalReplace(s.data[h.r]?.[h.c],term,replacement)}))
   .filter(h=>h.replacement!==null);
  if(!candidates.length)return notify(all?'置換する文字列セルはありません。':'検索結果の文字列セルを選んでから置換してください。');
  if(all&&!window.confirm(candidates.length+'セルを置換しますか？数値と数式は変更しません。'))return '中止しました。';
  for(const h of candidates)api().setCellValue(h.r,h.c,h.replacement===''?'':"'"+h.replacement);
  api().calculateFormula?.();changed();
  return notify(candidates.length+'セルの文字列を置換しました。');
 });
 const sort=(direction)=>guard(()=>{
  const s=sheet();const {c}=currentFocus();
  assertSheetEditable(s);onCanRestructure?.();
  if(filterActive||hiddenRef.current.length)throw Error('フィルターを解除してから並べ替えてください。');
  if(features?.length)throw Error('元ファイルに高度なExcel機能があります。安全のため並べ替えを制限しています。');
  if(usedRows(s)>5000)throw Error('5,000行を超える表は未対応です。');
  if(!window.confirm('1行目を見出しとして残し、'+coordToA1(0,c).replace(/[0-9]+$/,'')+'列を基準に行全体を'+(direction==='asc'?'昇順':'降順')+'に並べ替えますか？'))return;
  onCanRestructure?.();
  const next=sortedSheet(s,c,direction);
  next.celldata=api().dataToCelldata(next.data);
  const all=structuredClone(api().getAllSheets());
  if(!s.id)throw Error('シートIDがありません。');
  onReplaceSheets(all.map(x=>x.id===s.id?next:x));
  changed(true);
  return notify('行全体を並べ替えました。安全保存は無効にしました。');
 });
 const filter=(term)=>guard(()=>{
  const s=sheet();assertSheetEditable(s);
  if(isMerged(s)||s.isPivotTable||s.filter||s.filter_select)throw Error('結合・既存フィルター・ピボットのあるシートは未対応です。');
  if(filteredSheetId.current && filteredSheetId.current!==s.id)throw Error('フィルター解除は元のシートに戻ってから実行してください。');
  assertFilterShape();
  const own=new Set(hiddenRef.current.map(String));
  const prior=Object.keys(s?.config?.rowhidden||{}).filter(r=>!own.has(r));
  if(prior.length)throw Error('既存の非表示行があるため変更しません。');
  const hidden=rowsNotMatching(s,currentFocus().c,term);
  if(hiddenRef.current.length)api().showRowOrColumn(hiddenRef.current,'row');
  if(hidden.length)api().hideRowOrColumn(hidden,'row');
  hiddenRef.current=hidden;filteredSheetId.current=s.id;filterShapeRef.current={row:s.row,column:s.column,dataLength:s.data.length};setFilterActive(true);onFilterStateChange?.(s.id);changed(true);
  return notify(Math.max(0,usedRows(s)-1-hidden.length)+'行を表示、'+hidden.length+'行を非表示にしました。');
 });
 const clearFilter=()=>guard(()=>{
  if(filteredSheetId.current && sheet().id!==filteredSheetId.current)throw Error('フィルターを設定したシートに戻ってから解除してください。');
  assertFilterShape();
  if(hiddenRef.current.length)api().showRowOrColumn(hiddenRef.current,'row');
  hiddenRef.current=[];filteredSheetId.current=null;filterShapeRef.current=null;setFilterActive(false);onFilterStateChange?.(null);changed(true);
  return notify('簡易フィルターを解除しました。');
 });
 const fillDown=(rows)=>guard(()=>{
  if(!Number.isInteger(rows)||rows<1||rows>100)throw Error('追加する行数は1〜100にしてください。');
  const s=sheet(),focus=currentFocus(),actual=explicitTargetRef?.current?null:api().getSelection?.()?.[0];assertSheetEditable(s);const selection=actual&&actual.row[0]===focus.r&&actual.row[1]===focus.r&&actual.column[0]<=focus.c&&actual.column[1]>=focus.c?actual:{row:[focus.r,focus.r],column:[focus.c,focus.c]};
  if(selection.row[0]!==selection.row[1])throw Error('元の選択範囲は1行だけにしてください。');
  if(selection.row[1]+rows>=(s.row||100))throw Error('シートの下端を越えます。行を追加してください。');
  if(isMerged(s))throw Error('結合セルのあるシートではオートフィルできません。');
  const target={row:[selection.row[1]+1,selection.row[1]+rows],column:[...selection.column]};
  api().autoFillCell(selection,target,'down');api().calculateFormula?.();changed(true);
  return notify(rows+'行にオートフィルしました。安全保存は無効にしました。');
 });
 const copyValues=async()=>{
  try{
   const focus=currentFocus(),actual=explicitTargetRef?.current?null:api().getSelection?.()?.[0]; const sel=actual&&actual.row[0]<=focus.r&&actual.row[1]>=focus.r&&actual.column[0]<=focus.c&&actual.column[1]>=focus.c?actual:{row:[focus.r,focus.r],column:[focus.c,focus.c]};
   const n=(sel.row[1]-sel.row[0]+1)*(sel.column[1]-sel.column[0]+1);
   if(n>1000)throw Error('コピーは1,000セルまでです。');
   if(!navigator.clipboard?.writeText)throw Error('このブラウザはコピーAPIを利用できません。');
   const data=[];let protectedCount=0;
   const liveSheet=api().getSheet?.();
   for(let r=sel.row[0];r<=sel.row[1];r++){
    const row=[];
    for(let c=sel.column[0];c<=sel.column[1];c++){
     const raw=api().getCellValue(r,c)??'';
     const source=liveSheet?.data?.[r]?.[c];
     const scalar=source?.v && typeof source.v==='object'?source.v.v:source?.v;
     const safe=typeof scalar==='number'?raw:escapeClipboardFormula(raw);
     if(safe!==raw)protectedCount++;
     row.push(safe);
    }
    data.push(row);
   }
   await navigator.clipboard.writeText(formatTsv(data));
   notify(n+'セルの値をコピーしました。'+(protectedCount?' 数式として扱われないよう'+protectedCount+'件の文字列に先頭記号を付けました。':''));
  }catch(e){notify('コピーできません: '+e.message);}
 };
 const pasteClipboard=async()=>{
  try{
   if(!navigator.clipboard?.readText)throw Error('クリップボードAPIが利用できません。');
   const text=await navigator.clipboard.readText();
   const {data}=validatePaste(text);
   onPaste(data);
  }catch(e){notify('クリップボードを直接読めません。手動貼り付け画面を開きます: '+e.message);onPasteFallback?.();}
 };
 const compare=async()=>{
  if(!sourceFile){notify('保存前比較は既存のXLSXファイルを開いたときに利用できます。');return;}
  if(working||busy)return;
  setWorking(true);
  try{
   const proposed=await transformFortuneToExcel(apiRef,'xlsx',false);
   const result=await auditExcelSave(sourceFile,proposed);
   onLastAudit(result);setAudit(result);
   notify('保存前の構造比較を表示しました。ファイルは保存していません。');
  }catch(e){notify('互換性比較できません: '+(e.message||String(e)));}
  finally{setWorking(false);}
 };
 const action=(name,fn)=> <button type="button" disabled={busy||working} onClick={fn}>{name}</button>;
 return <>
  <div className="sheet-extras" aria-label="表の便利な操作">
   <span className="sheet-extras-label">便利な操作</span>
   {action('検索・置換',()=>setDialog('search'))}
   {action('昇順',()=>sort('asc'))}{action('降順',()=>sort('desc'))}
   {action('絞り込み',()=>setDialog('filter'))}
   {filterActive&&action('絞り込み解除',clearFilter)}
   {action('オートフィル',()=>setDialog('fill'))}
   {action('値をコピー',copyValues)}{action('値を貼り付け',pasteClipboard)}
   {action('保存前比較',compare)}
  </div>
  {dialog&&<SheetToolsDialog key={dialog} mode={dialog} address={coordToA1(currentFocus().r,currentFocus().c)} onClose={()=>setDialog(null)} onFind={findNext} onReplace={replace} onFilter={filter} onClearFilter={clearFilter} onFill={fillDown} filterActive={filterActive}/>}
  {audit&&<div className="shade" onMouseDown={e=>{if(e.target===e.currentTarget)setAudit(null);}}>
   <div className="dialog" role="dialog" aria-modal="true" aria-label="保存前の互換性比較">
    <div className="dialog-title"><div><small>COMPATIBILITY PREVIEW</small><h2>保存前の互換性比較</h2></div><button onClick={()=>setAudit(null)} aria-label="閉じる">×</button></div>
    <div className="dialog-body"><p>元のXLSXと、通常保存した場合のXML要素の件数差分です。件数が同じでも内容やレイアウトの一致は保証できません。</p>
    <table className="sheet-compare-table"><thead><tr><th>機能</th><th>元</th><th>出力予定</th><th>判定</th></tr></thead><tbody>
     {audit.original.features.map(x=>{const after=audit.output.features.find(y=>y.id===x.id)?.count??0;return <tr key={x.id}><td>{x.label}</td><td>{x.count}</td><td>{after}</td><td>{after<x.count?'減少 '+(x.count-after):'件数維持'}</td></tr>})}
    </tbody></table>
    <p className="sheet-tool-note">{audit.losses.length?'注意：'+audit.losses.length+'種類の機能で件数減少を検出しました。':'検出対象の件数減少はありません。ただし完全互換ではありません。'}</p>
    </div><div className="dialog-actions"><button className="primary" onClick={()=>setAudit(null)}>閉じる</button></div>
   </div>
  </div>}
 </>;
}
