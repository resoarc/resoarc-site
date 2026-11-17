import React,{useEffect,useState} from 'react';
import './save-format.css';

/**
 * The formats represent different guarantees; selecting a format does not
 * magically preserve unsupported OOXML structures.
 */
export default function SaveFormatDialog({hasSource,safeReady,hasAdvanced=false,onClose,onSave}){
 const [mode,setMode]=useState(hasSource&&safeReady?'preserve':'xlsx');
 const [acceptLoss,setAcceptLoss]=useState(false);
 const [busy,setBusy]=useState(false);
 const options=[
  {id:'preserve',label:'Excel機能を保持して保存',ext:'.preserved.xlsx',disabled:!hasSource||!safeReady,
   note:'元のXLSXのグラフ・画像・既存書式を維持。既存セルの値・数式のみ変更可能。行・列・書式の変更は保存できません。'},
  {id:'xlsx',label:'標準XLSXで保存',ext:'.xlsx',disabled:false,
   note:'現在の表データと編集内容をXLSXに再構成。元ファイルの画像・グラフ・条件付き書式などが失われる場合があります。'},
  {id:'csv',label:'CSVで保存',ext:'.csv',disabled:false,
   note:'現在の1シートの値を保存。複数シート・書式・Excel数式は保持しません。'},
  {id:'json',label:'ResoArc編集バックアップ',ext:'.resoarc.json',disabled:false,
   note:'ResoArc Sheetに戻すための編集データ。Excelでは直接開けません。元の画像・グラフの保持形式ではありません。'},
 ];
 const selected=options.find(x=>x.id===mode);
 const lossConsent=hasSource&&mode==='xlsx';
 const blocked=selected?.disabled||(lossConsent&&!acceptLoss)||busy;
 useEffect(()=>{
  const handle=e=>{if(e.key==='Escape'){e.stopPropagation();if(!busy)onClose();}};
  window.addEventListener('keydown',handle,true);
  return()=>window.removeEventListener('keydown',handle,true);
 },[busy,onClose]);
 const submit=async e=>{
  e.preventDefault();
  if(blocked)return;
  setBusy(true);
  try{await onSave(mode,{acceptLoss:lossConsent&&acceptLoss});}
  finally{setBusy(false);}
 };
 return <div className="save-choice-overlay" onMouseDown={e=>{if(e.target===e.currentTarget&&!busy)onClose();}}>
  <form className="save-choice-dialog" role="dialog" aria-modal="true" aria-labelledby="save-choice-heading" onSubmit={submit}>
   <header><div><small>EXPORT FORMAT</small><h2 id="save-choice-heading">形式を選んで保存</h2></div><button type="button" onClick={onClose} disabled={busy} aria-label="閉じる">×</button></header>
   <div className="save-choice-content">
    <p>目的に合わせて保存形式を選んでください。元ファイルは上書きしません。</p>
    <fieldset><legend className="sr-only">保存形式</legend>
      {options.map(o=><label key={o.id} className={'save-choice-option'+(mode===o.id?' chosen':'')+(o.disabled?' unavailable':'')}>
       <input type="radio" name="save-format" value={o.id} checked={mode===o.id} disabled={o.disabled||busy}
        onChange={()=>{setMode(o.id);setAcceptLoss(false);}}/>
       <span className="save-choice-copy"><strong>{o.label} <small>{o.ext}</small></strong><span>{o.note}</span>
        {o.disabled&&o.id==='preserve'&&<em>元のXLSXの読込と安全保存の準備が必要です。</em>}
       </span>
      </label>)}
    </fieldset>
    {lossConsent&&<div className="save-choice-warning" role="note">
     <strong>高度なExcel機能の保持を保証しません</strong>
     <p>{hasAdvanced?'元ファイルに高度な機能が検出されています。':'既存のXLSXを再構成するため、失われる機能がないか保存時に比較します。'} 標準XLSXを選んだ場合、保存前に実際に失われる要素を表示します。</p>
     <label><input type="checkbox" aria-label="高度なExcel機能が失われても標準XLSXを作成する" checked={acceptLoss} onChange={e=>setAcceptLoss(e.target.checked)}/>
      <span>必要な情報が失われる可能性を理解し、別名の簡易版XLSXを作成することに同意します。</span></label>
    </div>}
    {mode==='preserve'&&<p className="save-choice-info">既存セルの値・数式以外を編集した場合は安全保存できません。変更内容を保持したい場合は、ResoArc編集バックアップも作成してください。</p>}
    {mode==='csv'&&<p className="save-choice-info">CSVはExcel特有の書式・数式を残しません。</p>}
   </div>
   <footer><button type="button" onClick={onClose} disabled={busy}>キャンセル</button><button type="submit" disabled={blocked} className="save-choice-apply">{busy?'保存処理中…':'この形式で保存'}</button></footer>
  </form>
 </div>;
}
