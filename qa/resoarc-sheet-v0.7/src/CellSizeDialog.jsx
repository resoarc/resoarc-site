import React,{useState} from 'react';
export default function CellSizeDialog({mode='column',initial=100,address,onCancel,onApply}){
 const isColumn=mode==='column';
 const [value,setValue]=useState(String(initial));
 const min=isColumn?25:18,max=isColumn?600:300;
 const num=Number(value);
 const valid=Number.isInteger(num)&&num>=min&&num<=max;
 return <div className="format-modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)onCancel()}}>
  <section role="dialog" aria-modal="true" aria-labelledby="cell-size-dialog-title" className="format-modal size-dialog">
   <header className="format-modal-header"><h2 id="cell-size-dialog-title">{isColumn?'列幅':'行の高さ'}の設定</h2><button className="format-modal-close" aria-label="閉じる" onClick={onCancel}>×</button></header>
   <form onSubmit={e=>{e.preventDefault();if(valid)onApply(num)}}>
    <div className="size-dialog-body"><p>選択セル <strong>{address}</strong> の{isColumn?'列幅':'行の高さ'}をピクセルで指定します。</p>
    <label htmlFor="size-input">{isColumn?'列幅':'行の高さ'}（{min}〜{max}px）</label>
    <input id="size-input" aria-label={isColumn?'列幅（ピクセル）':'行の高さ（ピクセル）'} type="number" min={min} max={max} step="1" required value={value} onChange={e=>setValue(e.target.value)} autoFocus/>
    <p className="paste-values-note">原本を保持する「安全保存」は列幅・行高の変更には対応しません。通常のXLSX保存を使用してください。</p></div>
    <footer className="format-modal-footer"><button type="button" onClick={onCancel}>キャンセル</button><button className="format-apply" type="submit" disabled={!valid}>適用</button></footer>
   </form>
  </section>
 </div>;
}
