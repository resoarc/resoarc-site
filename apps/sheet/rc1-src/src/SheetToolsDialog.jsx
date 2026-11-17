import React,{useState} from 'react';

export default function SheetToolsDialog({mode,address,onClose,onFind,onReplace,onFilter,onClearFilter,onFill,filterActive}){
 const [term,setTerm]=useState(''),[replacement,setReplacement]=useState(''),[rows,setRows]=useState(5),[note,setNote]=useState('');
 const title={search:'検索・置換',filter:'列の簡易フィルター',fill:'下方向にオートフィル'}[mode];
 const perform=fn=>{try{const result=fn();setNote(result||'完了しました。');}catch(e){setNote(e.message||String(e));}};
 return <div className="shade" onMouseDown={e=>{if(e.target===e.currentTarget)onClose();}}>
  <div className="dialog sheet-tool-dialog" role="dialog" aria-modal="true" aria-label={title}>
   <div className="dialog-title"><div><small>SHEET TOOLS</small><h2>{title}</h2></div><button type="button" onClick={onClose} aria-label="閉じる">×</button></div>
   <div className="dialog-body">
    {mode==='search'&&<>
     <p>現在のシートで文字を探します。置換は文字列のセルだけが対象で、数式と数値セルは変更しません。</p>
     <label className="sheet-tool-field">検索する文字<input autoFocus value={term} onChange={e=>setTerm(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')perform(()=>onFind(term));}} maxLength={200}/></label>
     <label className="sheet-tool-field">置換後の文字<input value={replacement} onChange={e=>setReplacement(e.target.value)} maxLength={500}/></label>
     <div className="sheet-tool-actions">
      <button type="button" onClick={()=>perform(()=>onFind(term))}>次を検索</button>
      <button type="button" onClick={()=>perform(()=>onReplace(term,replacement,false))}>選択セルを置換</button>
      <button type="button" onClick={()=>perform(()=>onReplace(term,replacement,true))}>すべて置換（最大500件）</button>
     </div>
    </>}
    {mode==='filter'&&<>
     <p>選択中の列（{address}）を対象に、1行目を見出しとして含む行だけを表示します。元のセル値は変更しません。既存の非表示行や結合セルのあるシートでは利用できません。</p>
     <label className="sheet-tool-field">含む文字<input autoFocus value={term} onChange={e=>setTerm(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')perform(()=>onFilter(term));}} maxLength={200}/></label>
     <div className="sheet-tool-actions"><button type="button" onClick={()=>perform(()=>onFilter(term))}>絞り込む</button><button type="button" disabled={!filterActive} onClick={()=>perform(onClearFilter)}>解除</button></div>
    </>}
    {mode==='fill'&&<>
     <p>選択した1行分のセルを基準に、下方向へ値・数式・書式をコピーします。数式の相対参照は表計算エンジンの機能に従います。</p>
     <label className="sheet-tool-field">追加する行数（1〜100）<input type="number" min="1" max="100" step="1" value={rows} onChange={e=>setRows(e.target.value)}/></label>
     <div className="sheet-tool-actions"><button type="button" onClick={()=>perform(()=>onFill(Number(rows)))}>オートフィルを実行</button></div>
    </>}
    {note&&<p className="sheet-tool-note" role="status">{note}</p>}
   </div>
   <div className="dialog-actions"><button type="button" onClick={onClose}>閉じる</button></div>
  </div>
 </div>;
}
