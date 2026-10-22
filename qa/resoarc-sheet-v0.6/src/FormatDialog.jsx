import React,{useEffect,useState} from 'react';
const CATEGORIES=[
 {value:'General',label:'標準'},
 {value:'0',label:'数値（整数）'},
 {value:'0.00',label:'数値（小数2桁）'},
 {value:'#,##0',label:'桁区切り'},
 {value:'#,##0.00',label:'桁区切り（小数2桁）'},
 {value:'0%',label:'パーセント（整数）'},
 {value:'0.00%',label:'パーセント（小数2桁）'},
 {value:'¥#,##0',label:'通貨（円）'},
 {value:'yyyy/mm/dd',label:'日付（yyyy/mm/dd）'},
 {value:'@',label:'文字列'}
];
const FONTS=['Yu Gothic','Meiryo','Arial','Noto Sans JP','Times New Roman'];
export default function FormatDialog({onClose,onApply,initial={}}){
 const [format,setFormat]=useState(initial.numberFormat||'General');
 const [font,setFont]=useState(initial.font||'Yu Gothic');
 const [size,setSize]=useState(initial.size||11);
 const [bold,setBold]=useState(initial.bold===true);
 const [italic,setItalic]=useState(initial.italic===true);
 const [horizontal,setHorizontal]=useState('keep');
 useEffect(()=>{const close=e=>{if(e.key==='Escape'){e.stopPropagation();onClose();}};window.addEventListener('keydown',close,true);return()=>window.removeEventListener('keydown',close,true);},[onClose]);
 return <div className="format-modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}>
 <section className="format-modal" role="dialog" aria-modal="true" aria-labelledby="cell-format-dialog-title">
  <header className="format-modal-header"><h2 id="cell-format-dialog-title">セルの書式設定</h2><button type="button" className="format-modal-close" onClick={onClose} aria-label="閉じる">×</button></header>
  <div className="format-modal-body">
   <fieldset><legend>表示形式</legend><label htmlFor="format-category">分類</label>
    <select id="format-category" value={format} onChange={e=>setFormat(e.target.value)}>
    {CATEGORIES.map(x=><option value={x.value} key={x.value}>{x.label}</option>)}</select>
    <small>既存の日時・通貨の表示にはExcel側の表示結果と差が出る場合があります。</small>
   </fieldset>
   <fieldset><legend>フォント</legend>
    <div className="format-field-row"><label htmlFor="format-font-family">フォント</label><select id="format-font-family" value={font} onChange={e=>setFont(e.target.value)}>{FONTS.map(x=><option value={x} key={x}>{x}</option>)}</select>
    <label htmlFor="format-font-size">サイズ</label><select id="format-font-size" value={size} onChange={e=>setSize(Number(e.target.value))}>{[8,9,10,11,12,14,16,18,20,24,28,32,36].map(x=><option value={x} key={x}>{x}</option>)}</select></div>
    <div className="format-checkboxes"><label><input type="checkbox" checked={bold} onChange={e=>setBold(e.target.checked)}/> 太字</label><label><input type="checkbox" checked={italic} onChange={e=>setItalic(e.target.checked)}/> 斜体</label></div>
   </fieldset>
   <fieldset><legend>配置</legend><label htmlFor="format-alignment">横位置</label>
     <select id="format-alignment" value={horizontal} onChange={e=>setHorizontal(e.target.value)}><option value="keep">現在の配置を維持</option><option value="left">左揃え</option><option value="center">中央揃え</option><option value="right">右揃え</option></select>
   </fieldset>
  </div>
  <footer className="format-modal-footer"><button type="button" onClick={onClose}>キャンセル</button><button type="button" className="format-apply" onClick={()=>onApply({numberFormat:format,font,size,bold,italic,horizontal})}>適用</button></footer>
 </section></div>;
}
