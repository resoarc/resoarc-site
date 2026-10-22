import React,{useMemo,useState} from 'react';
import {validatePaste} from './paste-values.mjs';
export default function PasteValuesDialog({address,onCancel,onApply}){
 const [content,setContent]=useState('');
 const preview=useMemo(()=>{try{return {ok:true,...validatePaste(content)};}catch(e){return {ok:false,message:e.message};}},[content]);
 return <div className="format-modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)onCancel()}}>
  <section className="format-modal paste-values-modal" role="dialog" aria-modal="true" aria-labelledby="paste-values-title">
   <header className="format-modal-header"><h2 id="paste-values-title">形式を選択して貼り付け：値のみ</h2><button className="format-modal-close" aria-label="閉じる" onClick={onCancel}>×</button></header>
   <div className="paste-values-body">
    <p>Excelや他の表計算ソフトでコピーしたセルを、下の欄に貼り付けてください。<strong>書式や数式を貼り付けず、値のみ</strong>を <strong>{address}</strong> を左上として入力します。</p>
    <textarea aria-label="貼り付ける値" autoFocus spellCheck={false} rows={8} value={content} onChange={e=>setContent(e.target.value)} placeholder={'品名\t数量\n鉛筆\t12\nノート\t7'}/>
    {preview.ok?<p className="paste-preview" role="status">{preview.rows}行 × {preview.columns}列、合計{preview.cellCount}セルを貼り付けます。</p>:<p className="paste-preview" role="status">プレビュー：{content?preview.message:'データを入力してください。'}</p>}
    <p className="paste-values-note">最大1,000セル。先頭ゼロの文字列は維持します。数式で始まる入力は拒否します。既存セルは上書きされるため、必要なら先にバックアップしてください。</p>
   </div>
   <footer className="format-modal-footer"><button onClick={onCancel}>キャンセル</button><button disabled={!preview.ok} className="format-apply" onClick={()=>onApply(preview.data)}>値を貼り付け</button></footer>
  </section>
 </div>;
}
