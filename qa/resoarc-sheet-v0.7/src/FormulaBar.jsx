import React,{useEffect,useState} from 'react';
function colName(index){let s='',i=index+1;while(i>0){i--;s=String.fromCharCode(65+i%26)+s;i=Math.floor(i/26);}return s;}
export function coordToA1(row,column){return colName(column)+(row+1);}
export function parseRange(text){
 const input=String(text||'').toUpperCase().replaceAll('$','').replace(/\s/g,'');
 const match=/^([A-Z]{1,3})([1-9]\d{0,6})(?::([A-Z]{1,3})([1-9]\d{0,6}))?$/.exec(input);
 if(!match)return null;
 const toNum=s=>[...s].reduce((n,ch)=>n*26+ch.charCodeAt(0)-64,0)-1;
 const r1=Number(match[2])-1,c1=toNum(match[1]),r2=match[4]?Number(match[4])-1:r1,c2=match[3]?toNum(match[3]):c1;
 if(Math.max(r1,r2)>100000||Math.max(c1,c2)>16383)return null;
 return {row:[Math.min(r1,r2),Math.max(r1,r2)],column:[Math.min(c1,c2),Math.max(c1,c2)]};
}
export default function FormulaBar({address,value,onGo,onSubmit,disabled}){
 const [addressInput,setAddressInput]=useState(address);
 const [formulaInput,setFormulaInput]=useState(value);
 useEffect(()=>setAddressInput(address),[address]);
 useEffect(()=>setFormulaInput(value),[value,address]);
 return <div className="excel-formula-bar" aria-label="名前ボックスと数式バー">
  <form className="formula-name" onSubmit={e=>{e.preventDefault();onGo(addressInput)}}><label className="sr-only" htmlFor="a1-name-box">名前ボックス</label><input id="a1-name-box" aria-label="名前ボックス" disabled={disabled} title="セル番地を入力してEnter（例: B12）" value={addressInput} onChange={e=>setAddressInput(e.target.value)} onBlur={()=>setAddressInput(address)}/></form>
  <span className="formula-divider" aria-hidden="true"/>
  <span className="formula-fx" aria-hidden="true">ƒx</span>
  <form className="formula-input-form" onSubmit={e=>{e.preventDefault();onSubmit(formulaInput)}}><label className="sr-only" htmlFor="formula-field">数式バー</label><input id="formula-field" aria-label="数式バー" value={formulaInput} disabled={disabled} onChange={e=>setFormulaInput(e.target.value)} onKeyDown={e=>{if(e.key==='Escape'){setFormulaInput(value);e.currentTarget.blur();}}} placeholder="セルの値または =SUM(A1:A5)" title="Enterで現在のセルに値または数式を入力"/></form>
 </div>;
}
