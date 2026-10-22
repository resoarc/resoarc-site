import React,{useEffect,useRef,useState,useMemo,useCallback} from 'react';
import {Workbook} from '@fortune-sheet/react';
import {transformExcelToFortune,transformFortuneToExcel} from '@corbe30/fortune-excel';
import {scanWorkbook} from './preflight.mjs';
import {numericCellsInXlsx,restoreNumericCells} from './numeric-types.mjs';
import {snapshotToInitialSheets} from './snapshot.mjs';
import {inspectXlsx,auditExcelSave,formatAuditMessage} from './compat-audit.mjs';
import {captureSnapshot,valueOnlyDiff} from './safe-diff.mjs';
import {patchOriginalWorkbook} from './safe-ooxml.mjs';
import Ribbon from './Ribbon.jsx';
import FormulaBar,{coordToA1,parseRange} from './FormulaBar.jsx';
import {setupJapaneseContextMenus} from './localize-menu.mjs';
import FormatDialog from './FormatDialog.jsx';

const MemoWorkbook=React.memo(Workbook);
const empty=()=>[{name:'Sheet1',celldata:[],row:100,column:26}];
const nameOf=n=>n.replace(/\.(xlsx|csv|json)$/i,'')||'新しいブック';
const downloadBlob=(name,blob)=>{const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);};
const download=(name,text)=>downloadBlob(name,new Blob([text],{type:'application/json'}));
export default function App(){
 const ref=useRef(null),fileRef=useRef(null),backupRef=useRef(null),saveRef=useRef(null),sourceRef=useRef(null);
 const baselineRef=useRef(null),baselinePendingRef=useRef(false);
 const [sheets,setSheets]=useState(empty),[key,setKey]=useState(0);
 const [name,setName]=useState('新しいブック'),[dirty,setDirty]=useState(false);
 const [busy,setBusy]=useState(false),[msg,setMsg]=useState('空のブックを作成しました。セルを選択して入力できます。');
 const [help,setHelp]=useState(false),[drag,setDrag]=useState(false),[formatDialog,setFormatDialog]=useState(false);
 const [features,setFeatures]=useState([]),[lastAudit,setLastAudit]=useState(null),[safeReady,setSafeReady]=useState(false);
 const [activeTab,setActiveTab]=useState('ホーム');
 const [selected,setSelected]=useState({r:0,c:0});
 const [formulaValue,setFormulaValue]=useState('');
 const [format,setFormat]=useState({font:'Yu Gothic',size:11,color:'#17273d',fill:'#ffffff'});
 const selectedRef=useRef({r:0,c:0});
 const engineHooks=useMemo(()=>({afterSelectionChange:(id,sel)=>queueMicrotask(()=>updateSelectedCell(sel))}),[]);
 const onEngineOp=useCallback(()=>queueMicrotask(()=>{setDirty(true);refreshFormula();}),[]);
 useEffect(()=>setupJapaneseContextMenus(),[]);
 const canDiscard=()=>!dirty||confirm('未保存の変更があります。破棄して開き直しますか？');
 async function load(file){
  if(!file||busy||!canDiscard())return;
  setBusy(true);
  try{
   if(file.name.toLowerCase().endsWith('.json')){
    if(file.size>20*1024*1024)throw Error('20MB以下のファイルを選んでください。');
    const obj=JSON.parse(await file.text());
    if(obj.format!=='resoarc-fortune-1'||!Array.isArray(obj.sheets)||!obj.sheets.length)throw Error('対応するResoArcバックアップではありません。');
    setSheets(snapshotToInitialSheets(obj.sheets));setKey(v=>v+1);setName(obj.name||nameOf(file.name));
    sourceRef.current=null;baselineRef.current=null;baselinePendingRef.current=false;setSafeReady(false);setFeatures([]);setLastAudit(null);
   }else{
    const risks=await scanWorkbook(file);
    if(risks.length&&!confirm('一部のExcel機能を再現できない可能性があります。\n'+risks.join('\n')+'\n元ファイルは保管されます。読み込みますか？'))return;
    const isExcel=file.name.toLowerCase().endsWith('.xlsx');
    const report=isExcel?await inspectXlsx(file):{features:[]};
    baselineRef.current=null;baselinePendingRef.current=isExcel;setSafeReady(false);
    sourceRef.current=isExcel?file:null;
    const numeric=await numericCellsInXlsx(file);
    const restoreSheets=(incoming)=>setSheets(prev=>restoreNumericCells(typeof incoming==='function'?incoming(prev):incoming,numeric));
    const sourceFile=file.name.toLowerCase().endsWith('.csv')
      ? new File([(await file.text()).replace(/\r\n/g,'\n')],file.name,{type:'text/csv'})
      : file;
    await transformExcelToFortune(sourceFile,restoreSheets,setKey,ref);
    setName(nameOf(file.name));
    setFeatures(report.features);setLastAudit(null);
   }
   setDirty(false);setMsg('読み込みました。編集後は別ファイルとして保存してください。');
  }catch(e){console.error(e);baselineRef.current=null;baselinePendingRef.current=false;setSafeReady(false);sourceRef.current=null;setMsg('読込エラー: '+(e.message||String(e)));}
  finally{setBusy(false);}
 }
 async function save(format){
  if(busy||!ref.current)return;
  setBusy(true);
  try{if(format==='csv'&&!window.confirm('CSVは現在の1シートのみ、書式や複数シート・数式情報を保持しません。別ファイルとして保存しますか？')){setMsg('CSV保存をキャンセルしました。');return;}
    const blob=await transformFortuneToExcel(ref,format,false);
    if(!(blob instanceof Blob)||blob.size<4)throw Error('保存データの生成に失敗しました。');
    if(format==='xlsx'&&sourceRef.current){
     const audit=await auditExcelSave(sourceRef.current,blob);
     setLastAudit(audit);
     if(audit.losses.length||audit.hasRisks){
      const summary=formatAuditMessage(audit);
      if(!window.confirm('【Excel互換性チェック】\n'+(audit.losses.length?'保存時に次の要素が減少・消失する可能性があります。':'元ファイルに特殊なExcel機能があります。')+'\n'+summary+'\n\n検出できない差分もあります。原本は残し、別ファイルをダウンロードしますか？')){
       setMsg('互換性リスクにより保存を中止しました。原本を保持しています。');return;
      }
     }
    }
    downloadBlob((name||'新しいブック')+'.'+format,blob);
    setDirty(false);setMsg(format.toUpperCase()+'を別ファイルで保存しました。原本は保持されています。');}
  catch(e){console.error(e);setMsg('保存エラー: '+(e.message||String(e)));}
  finally{setBusy(false);}
 }
 async function savePreserving(){
  if(busy||!safeReady||!sourceRef.current||!baselineRef.current){setMsg('安全保存の準備ができていません。XLSXを読み直してください。');return;}
  setBusy(true);
  try {
   const live=ref.current?.getAllSheets?.();
   const changes=valueOnlyDiff(baselineRef.current,live);
   const {blob,count}=await patchOriginalWorkbook(sourceRef.current,changes);
   const audit=await auditExcelSave(sourceRef.current,blob);
   setLastAudit(audit);
   if(audit.losses.length)throw Error('保存後に構造要素が減少しました。安全保存を中止します。');
   if(!window.confirm('【安全保存：既存セルの値・数式のみ】\n変更セル：'+count+'件\n元のXLSXの画像・グラフなどの関連ファイルを保持します。\n\n行列の追加、書式変更などには非対応です。Excelで数式を再計算するまで結果が古い場合があります。原本を残した別ファイルとして保存しますか？')){
    setMsg('安全保存をキャンセルしました。元ファイルは変更していません。');return;
   }
   downloadBlob((name||'新しいブック')+'.preserved.xlsx',blob);
   setDirty(false);setMsg('安全保存完了：'+count+'セルの値・数式だけを反映しました。原本は変更していません。');
  } catch(e){console.error(e);setMsg('安全保存できません: '+(e.message||String(e)));}
  finally{setBusy(false);}
 }
 function saveBackup(){
  try{const data=ref.current?.getAllSheets?.();if(!Array.isArray(data)||!data.length)throw Error('編集データを取得できません。');
   download(name+'.resoarc.json',JSON.stringify({format:'resoarc-fortune-1',name,sheets:data,createdAt:new Date().toISOString()}));
   setDirty(false);setMsg('ResoArc編集データをJSON形式で保存しました。');
  }catch(e){setMsg('JSON保存エラー: '+e.message);}
 }
 function refreshFormula(){
  const api=ref.current;if(!api?.getCellValue)return;
  const {r,c}=selectedRef.current;
  try{
   const formula=api.getCellValue(r,c,{type:'f'});
   const raw=api.getCellValue(r,c);
   setFormulaValue(typeof formula==='string'&&formula?('='+formula.replace(/^=/,'')):(raw==null?'':String(raw)));
  }catch(e){console.debug('formula refresh',e);}
 }
 function updateSelectedCell(selection){
  if(!selection)return;
  const item=Array.isArray(selection)?selection[0]:selection;
  const r=item?.row_focus??item?.row?.[0],c=item?.column_focus??item?.column?.[0];
  if(!Number.isInteger(r)||!Number.isInteger(c)||r<0||c<0)return;
  selectedRef.current={r,c};setSelected({r,c});
  try{
   const api=ref.current;
   const formula=api?.getCellValue?.(r,c,{type:'f'});
   const value=api?.getCellValue?.(r,c);
   setFormulaValue(typeof formula==='string'&&formula?'='+formula.replace(/^=/,''):(value==null?'':String(value)));
   const size=api?.getCellValue?.(r,c,{type:'fs'});
   const color=api?.getCellValue?.(r,c,{type:'fc'});
   setFormat(old=>({...old,...(Number.isInteger(size)&&size>=8&&size<=36?{size}:{}),...(typeof color==='string'&&/^#[0-9a-f]{6}$/i.test(color)?{color}:{})}));
  }catch(e){console.debug('selection refresh',e);}
 }
 function goToAddress(text){
  const selection=parseRange(text);
  if(!selection){setMsg('セル番地が正しくありません。例：A1 または B2:D10');return;}
  try{ref.current?.setSelection?.([selection]);ref.current?.scroll?.({targetRow:selection.row[0],targetColumn:selection.column[0]});updateSelectedCell(selection);}
  catch(e){setMsg('セル移動に失敗しました：'+e.message);}
 }
 function submitFormula(input){
  try{
   const api=ref.current,{r,c}=selectedRef.current;
   if(!api?.setCellValue)throw Error('編集エンジンが利用できません。');
   const raw=String(input);
   const target=api.getSheet?.();
   if(Array.isArray(target?.data)){
    while(target.data.length<=r)target.data.push([]);
    if(!Array.isArray(target.data[r]))target.data[r]=[];
    while(target.data[r].length<=c)target.data[r].push(null);
   }
   api.setCellValue(r,c,raw.startsWith('=')?raw:(raw.trim()!==''&&/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?$/i.test(raw)&&!(raw.length>1&&/^0\d/.test(raw))?Number(raw):raw));
   api.calculateFormula?.();
   setDirty(true);setMsg(coordToA1(r,c)+' に入力しました。');
   queueMicrotask(refreshFormula);
  }catch(e){setMsg('数式バーの入力に失敗しました：'+e.message);}
 }
 function runRibbonCommand(command,payload){
  if(busy)return;
  const api=ref.current,{r,c}=selectedRef.current;
  const range=api?.getSelection?.()?.length?api.getSelection():[{row:[r,r],column:[c,c]}];
  const apply=(key,value)=>{api?.setCellFormatByRange?.(key,value,range);setDirty(true);};
  try{
   if(command==='new')return create();
   if(command==='open')return fileRef.current?.click();
   if(command==='save')return save('xlsx');
   if(command==='safe')return savePreserving();
   if(command==='csv')return save('csv');
   if(command==='backup')return saveBackup();
   if(command==='restore')return backupRef.current?.click();
   if(command==='formatDialog')return setFormatDialog(true);
   if(command==='help')return setHelp(true);
   if(command==='audit')return lastAudit?saveAuditReport():setHelp(true);
   if(!api)throw Error('編集画面の準備ができていません。');
   switch(command){
    case 'undo':api.handleUndo();break;
    case 'redo':api.handleRedo();break;
    case 'bold':apply('bl',api.getCellValue(r,c,{type:'bl'})===1?0:1);break;
    case 'italic':apply('it',api.getCellValue(r,c,{type:'it'})===1?0:1);break;
    case 'underline':apply('un',api.getCellValue(r,c,{type:'un'})===1?0:1);break;
    case 'font':apply('ff',payload);setFormat(f=>({...f,font:payload}));break;
    case 'fontSize':apply('fs',payload);setFormat(f=>({...f,size:payload}));break;
    case 'fontColor':apply('fc',payload);setFormat(f=>({...f,color:payload}));break;
    case 'fill':apply('bg',payload);setFormat(f=>({...f,fill:payload}));break;
    case 'left':apply('ht',1);break;
    case 'center':apply('ht',0);break;
    case 'right':apply('ht',2);break;
    case 'general':apply('ct',{fa:'General',t:'n'});break;
    case 'percent':apply('ct',{fa:'0.00%',t:'n'});break;
    case 'decimal':apply('ct',{fa:'0.00',t:'n'});break;
    case 'clear':for(const s of range)for(let y=s.row[0];y<=s.row[1];y++)for(let x=s.column[0];x<=s.column[1];x++)api.clearCell(y,x);setDirty(true);break;
    case 'insertRow':api.insertRowOrColumn('row',r,1,'lefttop');setDirty(true);break;
    case 'insertCol':api.insertRowOrColumn('column',c,1,'lefttop');setDirty(true);break;
    case 'addSheet':api.addSheet();setDirty(true);break;
    case 'freezeRow':api.freeze('row',{row:0,column:0});setDirty(true);break;
    case 'freezeCol':api.freeze('column',{row:0,column:0});setDirty(true);break;
    case 'unfreeze':api.freeze('both',{row:-1,column:-1});setDirty(true);break;
    case 'sum':case 'average':case 'max':case 'min':{
     const fn=command.toUpperCase();submitFormula('='+fn+'(A1:A'+Math.max(1,r)+')');return;
    }
    default:setMsg('この機能はまだ実装されていません：'+command);return;
   }
   queueMicrotask(refreshFormula);
  }catch(e){console.error(e);setMsg('操作できません：'+(e.message||String(e)));}
 }
 function applyCellFormat(values){
  const api=ref.current;
  if(!api){setMsg('書式設定できません。');return;}
  try{
   const {r,c}=selectedRef.current;
   const ranges=api.getSelection?.()?.length?api.getSelection():[{row:[r,r],column:[c,c]}];
   api.setCellFormatByRange('ct',{fa:values.numberFormat,t:values.numberFormat==='@'?'s':'n'},ranges);
   api.setCellFormatByRange('ff',values.font,ranges);
   api.setCellFormatByRange('fs',values.size,ranges);
   api.setCellFormatByRange('bl',values.bold?1:0,ranges);
   api.setCellFormatByRange('it',values.italic?1:0,ranges);
   if(values.horizontal!=='keep')api.setCellFormatByRange('ht',values.horizontal==='left'?1:values.horizontal==='center'?0:2,ranges);
   setFormat(prev=>({...prev,font:values.font,size:values.size}));
   setDirty(true);
   setFormatDialog(false);
   setMsg('セルの書式を設定しました。XLSX保存で反映できます。');
   queueMicrotask(refreshFormula);
  }catch(e){console.error(e);setMsg('書式変更に失敗しました: '+e.message);}
 }
 function saveAuditReport(){
  if(!lastAudit)return;
  const report={format:'resoarc-sheet-compat-report-1',createdAt:new Date().toISOString(),workbook:name,
    note:'XML要素の件数差分を検査します。内容の完全な保持は保証しません。',
    original:lastAudit.original,exported:lastAudit.output,losses:lastAudit.losses};
  download((name||'book')+'.compat-report.json',JSON.stringify(report,null,2));
  setMsg('互換性監査レポートをJSONで保存しました。セル値は含みません。');
 }
 function create(){
  if(busy||!canDiscard())return;
  setSheets(empty());setKey(k=>k+1);setName('新しいブック');setDirty(false);setMsg('新しいブックを作成しました。');sourceRef.current=null;baselineRef.current=null;baselinePendingRef.current=false;setSafeReady(false);setFeatures([]);setLastAudit(null);
 }
 useEffect(()=>{
  const handler=e=>{
   const target=e.target;
   const editable=target instanceof HTMLElement && (target.matches('input,textarea,select')||target.isContentEditable);
   const dialogOpen=!!document.querySelector('[role="dialog"][aria-modal="true"]');
   if(dialogOpen||editable)return;
   if(e.key==='F2'&&!e.ctrlKey&&!e.altKey&&!e.metaKey){
    e.preventDefault();e.stopPropagation();
    const input=document.getElementById('formula-field');
    if(input){input.focus();input.setSelectionRange(input.value.length,input.value.length);}
    return;
   }
   if((e.ctrlKey||e.metaKey)&&e.key==='1'&&!e.shiftKey&&!e.altKey){
    e.preventDefault();e.stopPropagation();setFormatDialog(true);
   }
  };
  window.addEventListener('keydown',handler,true);
  return()=>window.removeEventListener('keydown',handler,true);
 },[]);
 saveRef.current=()=>save('xlsx');
 useEffect(()=>{
  if(!baselinePendingRef.current)return;
  const timer=setTimeout(()=>{
   if(!baselinePendingRef.current||!sourceRef.current)return;
   try{const current=ref.current?.getAllSheets?.();
    if(Array.isArray(current)&&current.length){baselineRef.current=captureSnapshot(current);baselinePendingRef.current=false;setSafeReady(true);}
   }catch(e){console.error('Baseline error',e);setMsg('安全保存用の初期状態を記録できませんでした。');}
  },450);
  return()=>clearTimeout(timer);
 },[key,sheets]);
 useEffect(()=>{
  const keys=e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();saveRef.current?.();}
                 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='o'){e.preventDefault();fileRef.current?.click();}};
  window.addEventListener('keydown',keys);
  return()=>window.removeEventListener('keydown',keys);
 },[]);
 useEffect(()=>{
  const leave=e=>{if(dirty){e.preventDefault();e.returnValue='';}};
  window.addEventListener('beforeunload',leave);
  return()=>window.removeEventListener('beforeunload',leave);
 },[dirty]);
 const onDrop=e=>{e.preventDefault();setDrag(false);if(e.dataTransfer.files?.[0])load(e.dataTransfer.files[0]);};
 return <div className="app">
  <header className="masthead">
   <div className="logo"><span className="logo-symbol">R<span>✣</span></span><span><strong>ResoArc <i>Sheet</i></strong><small>LOCAL SPREADSHEET</small></span></div>
   <span className="masthead-divider"/>
   <label className="name-field"><small>ワークブック名</small><input value={name} onChange={e=>{setName(e.target.value);setDirty(true);}} aria-label="ワークブック名" /></label>
   <div className="meta"><span className={'saved-indicator'+(dirty?' unsaved':'')}>{dirty?'● 未保存':'● ローカル編集中'}</span><span className="version">QA PREVIEW · 0.6</span></div>
  </header>
  <main className="content">
   <nav className="toolbar legacy-toolbar" aria-label="ファイル操作">
    <button disabled={busy} onClick={create}><span>＋</span> 新規</button>
    <button disabled={busy} onClick={()=>fileRef.current?.click()}><span>▤</span> 開く</button>
    <span className="rule"/>
    <button disabled={busy} className="primary" onClick={()=>save('xlsx')}><span>↓</span> XLSX保存</button>
    {sourceRef.current&&<button disabled={busy||!safeReady} onClick={savePreserving} title="既存セルの値だけ反映し、画像・グラフ等の元ファイル構造を保持します">◇ 安全保存</button>}
    <button disabled={busy} onClick={()=>save('csv')}>CSV保存</button>
    <span className="rule"/>
    <button disabled={busy} onClick={saveBackup}>JSONバックアップ</button>
    <button disabled={busy} onClick={()=>backupRef.current?.click()}>JSON復元</button>
    {lastAudit&&<button disabled={busy} onClick={saveAuditReport}>互換性監査JSON</button>}
    <button className="help" onClick={()=>setHelp(true)}>ⓘ 使い方・互換性</button>
   </nav>
   <Ribbon tab={activeTab} onTab={setActiveTab} busy={busy} hasSource={!!sourceRef.current} safeReady={safeReady} onCommand={runRibbonCommand} format={format} filename={name}/>
   <FormulaBar address={coordToA1(selected.r,selected.c)} value={formulaValue} disabled={busy} onGo={goToAddress} onSubmit={submitFormula}/>
   <div className="notice-line"><span>✓ ファイルはブラウザ内で処理します</span><span className="warn">{features.length?'⚠ 元ファイルの要注意機能 '+features.length+' 種類を検出。保存時に追加確認します。':'⚠ Excelと完全互換ではありません。元ファイルは残してください。'}</span></div>
   <section className={'grid-wrap'+(drag?' is-dragging':'')} onDragEnter={e=>{e.preventDefault();setDrag(true);}} onDragOver={e=>e.preventDefault()} onDragLeave={e=>{if(!e.currentTarget.contains(e.relatedTarget))setDrag(false);}} onDrop={onDrop}>
    <MemoWorkbook key={key} data={sheets} ref={ref} lang="en" showToolbar={false} showFormulaBar={false} defaultFontSize={11} hooks={engineHooks} onOp={onEngineOp}/>
    {drag&&<div className="drop-layer"><span>▤</span><strong>ここにファイルをドロップ</strong><small>.xlsx / .csv / .json</small></div>}
   </section>
   <footer className="statusbar"><div><span className={'pulse'+(busy?' in-progress':'')}/><span role="status" aria-live="polite">{busy?'処理しています…':msg}</span></div><span className="keys">Ctrl+O 開く / Ctrl+S 保存　　ResoArc Sheet</span></footer>
  </main>
  <input ref={fileRef} hidden type="file" accept=".xlsx,.csv" onChange={e=>{const f=e.target.files?.[0];e.target.value='';if(f)load(f);}}/>
  <input ref={backupRef} hidden type="file" accept=".json" onChange={e=>{const f=e.target.files?.[0];e.target.value='';if(f)load(f);}}/>
  {formatDialog&&<FormatDialog initial={{font:format.font,size:format.size,bold:ref.current?.getCellValue?.(selectedRef.current.r,selectedRef.current.c,{type:'bl'})===1,italic:ref.current?.getCellValue?.(selectedRef.current.r,selectedRef.current.c,{type:'it'})===1,numberFormat:ref.current?.getCellValue?.(selectedRef.current.r,selectedRef.current.c,{type:'ct'})?.fa||'General'}} onClose={()=>setFormatDialog(false)} onApply={applyCellFormat}/>}
  {help&&<div className="shade" onMouseDown={e=>{if(e.target===e.currentTarget)setHelp(false);}}>
   <div className="dialog" role="dialog" aria-modal="true" aria-label="使い方">
    <div className="dialog-title"><div><small>HELP & COMPATIBILITY</small><h2>使い方と制限事項</h2></div><button onClick={()=>setHelp(false)} aria-label="閉じる">×</button></div>
    <div className="dialog-body">
     <h3>基本操作</h3><p>「開く」で.xlsxや.csvを選択。セルをクリックして直接編集できます。関数は = から入力します。編集後は「XLSX保存」で新しいファイルをダウンロードします。元ファイルは上書きしません。</p>
     <h3>ローカル処理</h3><p>ログインは不要で、選んだファイルを外部サーバーにはアップロードしません。自動保存はありません。画面を閉じる前に保存してください。</p>
     <h3>Excel互換性（重要）</h3><p>初期QA版です。Excelの完全コピーではありません。マクロ・旧形式.xls・パスワード付きファイルは非対応。グラフ、画像、ピボット、印刷設定、条件付き書式、複雑な数式などは保存時に失われることがあります。必ず原本のコピーで試してください。</p>
     {features.length>0&&<><h3>現在のファイルで検出した要注意機能</h3><p>{features.map(x=>x.label+' '+x.count+'件').join('、')}</p></>}
     {lastAudit&&<><h3>直近の保存前監査</h3><p>{lastAudit.losses.length?formatAuditMessage(lastAudit):'検出できる要素の件数減少はありません。ただし内容の完全な一致は保証しません。'}</p></>}
     <h3>安全保存（既存XLSXのみ）</h3><p>元ファイルの構造を活用して、変更した既存セルの値や数式だけを更新します。画像・グラフ・印刷設定など、編集していない構造の欠落を避ける方式です。セルの追加・削除、行・列の移動、書式やシート構造の変更には対応しません。対応外の場合は保存を拒否し、通常保存には自動で切り替えません。既存の数式結果はExcelで開いて再計算されるまで古い場合があります。</p><h3>JSONバックアップ</h3><p>編集中のシート状態をResoArc独自形式で保存・復元します。元Excelの内部構造を保持するものではありません。</p>
    </div><div className="dialog-actions"><button className="primary" onClick={()=>setHelp(false)}>閉じる</button></div>
   </div>
  </div>}
 </div>;
}
