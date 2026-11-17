import test from 'node:test';
import assert from 'node:assert/strict';
import {File as NodeFile} from 'node:buffer';
import JSZip from 'jszip';
import {normalizeXlsxForImport} from '../src/xlsx-import-compat.mjs';

if(!globalThis.File)globalThis.File=NodeFile;
const main='http://schemas.openxmlformats.org/spreadsheetml/2006/main';
async function makeZip(prefixed=true){
 const zip=new JSZip();
 zip.file('xl/workbook.xml',prefixed
  ? '<x:workbook xmlns:x="'+main+'"><x:sheets><x:sheet name="A" sheetId="1"/></x:sheets></x:workbook>'
  : '<workbook xmlns="'+main+'"><sheets><sheet name="A" sheetId="1"/></sheets></workbook>');
 zip.file('xl/styles.xml',prefixed
  ? '<x:styleSheet xmlns:x="'+main+'"><x:borders count="2"><x:border /><x:border /></x:borders><x:fonts><x:font /></x:fonts></x:styleSheet>'
  : '<styleSheet xmlns="'+main+'"><borders count="1"><border/></borders></styleSheet>');
 zip.file('xl/worksheets/sheet1.xml',prefixed
  ? '<x:worksheet xmlns:x="'+main+'"><x:sheetData><x:row r="1"><x:c r="A1" t="inlineStr"><x:is><x:t>文字</x:t></x:is></x:c></x:row></x:sheetData></x:worksheet>'
  : '<worksheet xmlns="'+main+'"><sheetData><row r="1"><c r="A1"><v>12</v></c></row></sheetData></worksheet>');
 zip.file('xl/media/image1.png',new Uint8Array([137,80,78,71,1,2,3]));
 return new File([await zip.generateAsync({type:'uint8array'})],'spec.xlsx',{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
}
test('SpreadsheetML namespace and spaced empty styles are normalized only on import copy',async()=>{
 const orig=await makeZip();const before=new Uint8Array(await orig.arrayBuffer());
 const copy=await normalizeXlsxForImport(orig);
 assert.notEqual(copy,orig);
 const z=await JSZip.loadAsync(await copy.arrayBuffer());
 const w=await z.file('xl/workbook.xml').async('string');
 assert.ok(w.includes('<workbook xmlns="'+main+'">'));
 assert.ok(w.includes('<sheet name="A"'));
 const st=await z.file('xl/styles.xml').async('string');
 assert.ok(st.includes('<border/>')&&st.includes('<font/>'));
 assert.ok(!st.includes('x:border')&&!st.includes('<border />'));
 assert.deepEqual(Buffer.from(await z.file('xl/media/image1.png').async('uint8array')),Buffer.from([137,80,78,71,1,2,3]));
 assert.deepEqual(Buffer.from(await orig.arrayBuffer()),Buffer.from(before));
});
test('Already compatible XLSX is reused byte-for-byte',async()=>{
 const file=await makeZip(false);
 assert.equal(await normalizeXlsxForImport(file),file);
});
test('CSV bypasses ZIP normalization',async()=>{
 const file=new File(['商品,価格\n'], 'rows.csv',{type:'text/csv'});
 assert.equal(await normalizeXlsxForImport(file),file);
});
