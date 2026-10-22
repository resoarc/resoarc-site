import JSZip from 'jszip';

// This restores typed OOXML numeric cells that FortuneExcel 2.3.4 currently
// imports as text. Values such as "003" deliberately remain text.
function elements(doc,localName){
 return Array.from(doc.getElementsByTagName('*')).filter(n=>n.localName===localName);
}
function xml(text){
 const doc=new DOMParser().parseFromString(text,'application/xml');
 if(elements(doc,'parsererror').length)throw new Error('Excel内部XMLを解析できませんでした。');
 return doc;
}
function pos(address){
 const m=/^([A-Za-z]+)([1-9][0-9]*)$/.exec(address);
 if(!m)return null;
 let col=0;
 for(const ch of m[1].toUpperCase())col=col*26+ch.charCodeAt(0)-64;
 return {r:Number(m[2])-1,c:col-1};
}
function normalizeTarget(s){
 let path=s.replaceAll('\\','/').replace(/^\//,'');
 if(!path.startsWith('xl/'))path='xl/'+path;
 const parts=[];
 for(const part of path.split('/')){if(part==='..')parts.pop();else if(part&&part!=='.')parts.push(part);}
 return parts.join('/');
}
export async function numericCellsInXlsx(file){
 if(!file.name.toLowerCase().endsWith('.xlsx'))return new Map();
 const archive=await JSZip.loadAsync(file);
 const workbook=archive.file('xl/workbook.xml');
 const rels=archive.file('xl/_rels/workbook.xml.rels');
 if(!workbook||!rels)throw new Error('Excelのシート情報を解析できません。');
 const workbookDoc=xml(await workbook.async('string'));
 const relsDoc=xml(await rels.async('string'));
 const ids=new Map(elements(relsDoc,'Relationship').map(el=>[el.getAttribute('Id'),el.getAttribute('Target')]));
 const result=new Map();
 for(const sheet of elements(workbookDoc,'sheet')){
  const name=sheet.getAttribute('name');
  const relationId=sheet.getAttribute('r:id')||sheet.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id');
  const target=ids.get(relationId);
  if(!name||!target)continue;
  const part=archive.file(normalizeTarget(target));
  if(!part)continue;
  const doc=xml(await part.async('string'));
  const cells=new Map();
  for(const cell of elements(doc,'c')){
   const type=cell.getAttribute('t');
   if(type&&type!=='n')continue;
   const valueNode=Array.from(cell.children).find(n=>n.localName==='v');
   if(!valueNode)continue;
   const numeric=Number(valueNode.textContent);
   if(!Number.isFinite(numeric)||valueNode.textContent.trim()==='')continue;
   const p=pos(cell.getAttribute('r')||'');
   if(p)cells.set(p.r+','+p.c,numeric);
  }
  result.set(name,cells);
 }
 return result;
}
function repairValue(cell,numeric){
 if(!cell||typeof cell!=='object'||typeof cell.v==='undefined')return cell;
 const v={...cell,v:numeric};
 if(cell.ct?.t==='s')v.ct={...cell.ct,t:'n'};
 if(cell.vt===2)v.vt=1;
 return v;
}
export function restoreNumericCells(sheets, numericBySheet){
 if(!Array.isArray(sheets))return sheets;
 return sheets.map(sheet=>{
  const numeric=numericBySheet.get(sheet.name);
  if(!numeric?.size)return sheet;
  const next={...sheet};
  if(Array.isArray(sheet.celldata)){
   next.celldata=sheet.celldata.map(item=>{
    const value=numeric.get(item.r+','+item.c);
    return value===undefined?item:{...item,v:repairValue(item.v,value)};
   });
  }
  if(Array.isArray(sheet.data)){
   next.data=sheet.data.map((row,r)=>Array.isArray(row)?
     row.map((cell,c)=>{const value=numeric.get(r+','+c);return value===undefined?cell:repairValue(cell,value);}):row);
  }
  return next;
 });
}
