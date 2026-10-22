import JSZip from 'jszip';
import {DOMParser,XMLSerializer} from '@xmldom/xmldom';
const NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const R_NS='http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const XML_NS='http://www.w3.org/XML/1998/namespace';
const byLocal=(node,name)=>Array.from(node?.childNodes||[]).filter(n=>n.nodeType===1&&n.localName===name);
const one=(node,name)=>byLocal(node,name)[0];
function parseXml(body){
 if(/<!DOCTYPE|<!ENTITY/i.test(body))throw Error('外部実体を含むXMLは処理できません。');
 let error;
 const xml=new DOMParser({onError:(level,message)=>{if(level!=='warning')error=message;}}).parseFromString(body,'application/xml');
 if(error||!xml?.documentElement)throw Error('Excel内部XMLの解析に失敗しました。');
 return xml;
}
function normalizeTarget(target){
 if(!target||/^https?:|^file:|^\.\.\//i.test(target))throw Error('不正なExcel内部参照を検出しました。');
 const raw=target.replaceAll('\\','/').replace(/^\//,'');
 const parts=(raw.startsWith('xl/')?raw:'xl/'+raw).split('/');
 const stack=[];
 for(const part of parts){if(part==='..'){if(!stack.length)throw Error('不正なXML参照です。');stack.pop();}
 else if(part&&part!=='.')stack.push(part);}
 const path=stack.join('/');
 if(!path.startsWith('xl/'))throw Error('ワークシート参照が不正です。');
 return path;
}
function coord(r,c){
 let num=c+1, col='';
 while(num>0){num--;col=String.fromCharCode(65+num%26)+col;num=Math.floor(num/26);}
 return col+(r+1);
}
function setValue(doc,cell,sem){
 const existingFormula=one(cell,'f');
 if(existingFormula&&(existingFormula.getAttribute('t')||'normal')!=='normal')
  throw Error('共有数式・配列数式の編集は安全保存に対応していません。');
 const rich=one(cell,'is');
 if(rich&&byLocal(rich,'r').length)throw Error('部分的な文字装飾のあるセルは安全保存できません。');
 for(const node of [...byLocal(cell,'v'),...byLocal(cell,'f'),...byLocal(cell,'is')])cell.removeChild(node);
 switch(sem.type){
  case 'blank': cell.removeAttribute('t');break;
  case 'number':{
   if(!Number.isFinite(sem.value))throw Error('数値が不正です。');
   cell.setAttribute('t','n');
   const v=doc.createElementNS(NS,'v');v.appendChild(doc.createTextNode(String(sem.value)));cell.appendChild(v);break;
  }
  case 'boolean':{
   cell.setAttribute('t','b');
   const v=doc.createElementNS(NS,'v');v.appendChild(doc.createTextNode(sem.value?'1':'0'));cell.appendChild(v);break;
  }
  case 'string':{
   cell.setAttribute('t','inlineStr');
   const is=doc.createElementNS(NS,'is'),t=doc.createElementNS(NS,'t');
   if(/^\s|\s$/.test(sem.value))t.setAttributeNS(XML_NS,'xml:space','preserve');
   t.appendChild(doc.createTextNode(sem.value));is.appendChild(t);cell.appendChild(is);break;
  }
  case 'formula':{
   cell.setAttribute('t','n');const f=doc.createElementNS(NS,'f');
   f.appendChild(doc.createTextNode(sem.formula));cell.appendChild(f);break;
  }
  default:throw Error('安全保存に対応しないセル値です。');
 }
}
function updateCalc(doc){
 let calc=one(doc.documentElement,'calcPr');
 if(!calc){
  calc=doc.createElementNS(NS,'calcPr');
  const ext=one(doc.documentElement,'extLst');
  if(ext)doc.documentElement.insertBefore(calc,ext);
  else doc.documentElement.appendChild(calc);
 }
 calc.setAttribute('calcMode','auto');
 calc.setAttribute('fullCalcOnLoad','1');
 calc.setAttribute('forceFullCalc','1');
}
function getSheetParts(zip,workbookDoc){
 const relText=zip.file('xl/_rels/workbook.xml.rels');
 if(!relText)throw Error('Excel内部シート参照がありません。');
 return relText.async('string').then(body=>{
  const relDoc=parseXml(body);
  const ids=new Map(Array.from(relDoc.getElementsByTagName('*')).filter(n=>n.localName==='Relationship').map(x=>[x.getAttribute('Id'),x.getAttribute('Target')]));
  const sheetList=Array.from(workbookDoc.getElementsByTagName('*')).filter(n=>n.localName==='sheet');
  return new Map(sheetList.map(s=>{
   const relation=s.getAttributeNS(R_NS,'id')||s.getAttribute('r:id');
   const target=ids.get(relation);
   if(!target)throw Error('Excelシートの参照先を解決できません。');
   return [s.getAttribute('name'),normalizeTarget(target)];
  }));
 });
}
export async function patchOriginalWorkbook(sourceFile,changes){
 if(!sourceFile?.name?.toLowerCase().endsWith('.xlsx'))throw Error('安全保存は既存の .xlsx ファイル専用です。');
 if(sourceFile.size>20*1024*1024)throw Error('安全保存で扱えるXLSXは20MBまでです。');
 if(!Array.isArray(changes))throw Error('変更履歴がありません。');
 if(changes.length>500)throw Error('安全保存は500セルまでです。');
 if(!changes.length)return {blob:new Blob([await sourceFile.arrayBuffer()],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}),count:0};
 const zip=await JSZip.loadAsync(await sourceFile.arrayBuffer());
 const paths=Object.keys(zip.files);
 if(paths.length>5000)throw Error('元ファイルの構造が大きすぎます。');
 const uncompressed=Object.values(zip.files).filter(f=>!f.dir).reduce((sum,f)=>sum+(f._data?.uncompressedSize||0),0);
 if(uncompressed>150*1024*1024)throw Error('展開後のXLSXが大きすぎるため安全保存を中止しました。');
 if(paths.some(p=>/^(?:_xmlsignatures\/|xl\/vbaProject|xl\/tables\/)/i.test(p)))
  throw Error('電子署名・マクロ・Excelテーブルを含むブックでは、安全保存を利用できません。');
 const file=zip.file('xl/workbook.xml');
 if(!file)throw Error('Excelのワークブック構造が見つかりません。');
 const workbook=parseXml(await file.async('string'));
 const pathForSheet=await getSheetParts(zip,workbook);
 const grouped=new Map();
 for(const change of changes){
  if(!pathForSheet.has(change.sheet))throw Error('対象シートが元ファイルに存在しません。');
  if(!Number.isInteger(change.r)||!Number.isInteger(change.c)||change.r<0||change.c<0)throw Error('不正なセル座標です。');
  const a=grouped.get(change.sheet)||[];a.push(change);grouped.set(change.sheet,a);
 }
 const serialize=new XMLSerializer();
 for(const [name,edits] of grouped){
  const path=pathForSheet.get(name),entry=zip.file(path);
  if(!entry)throw Error(name+' の元XMLがありません。');
  if((entry._data?.uncompressedSize||0)>5*1024*1024)throw Error('シートXMLが大きすぎます。');
  const doc=parseXml(await entry.async('string'));
  const protection=one(doc.documentElement,'sheetProtection');
  if(protection)throw Error('保護されたシートは安全保存できません。');
  const data=one(doc.documentElement,'sheetData');
  if(!data)throw Error('シートデータがありません。');
  const rows=new Map(byLocal(data,'row').map(row=>[Number(row.getAttribute('r')),row]));
  for(const change of edits){
   const address=coord(change.r,change.c);
   const row=rows.get(change.r+1);
   if(!row)throw Error(address+' は元ファイルに存在しない行です。安全保存ではセル追加を行いません。');
   const cell=byLocal(row,'c').find(c=>c.getAttribute('r')===address);
   if(!cell)throw Error(address+' は元ファイルに存在しないセルです。安全保存ではセル追加を行いません。');
   const hyperlink=one(doc.documentElement,'hyperlinks');
   if(hyperlink&&byLocal(hyperlink,'hyperlink').some(h=>h.getAttribute('ref')===address))throw Error(address+' はハイパーリンク付きセルです。安全保存には対応できません。');
   setValue(doc,cell,change.after);
  }
  zip.file(path,serialize.serializeToString(doc));
 }
 updateCalc(workbook);
 zip.file('xl/workbook.xml',serialize.serializeToString(workbook));
 const blob=await zip.generateAsync({type:'blob',compression:'DEFLATE',compressionOptions:{level:6}});
 return {blob,count:changes.length,partsTouched:[...grouped.keys()].map(x=>pathForSheet.get(x))};
}
