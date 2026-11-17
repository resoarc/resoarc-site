import test from 'node:test';
import assert from 'node:assert/strict';
import ExcelJS from 'exceljs';
import {normalizeXlsxForExcel} from '../src/xlsx-export-compat.mjs';

test('ExcelJS normalization keeps multi-sheet formulas, strings and number formats',async()=>{
 const w=new ExcelJS.Workbook();
 const a=w.addWorksheet('売上'); a.getCell('A1').value='商品';
 a.getCell('A2').value='00001234';a.getCell('A2').numFmt='@';
 a.getCell('B2').value=5;a.getCell('C2').value={formula:'B2*2',result:10};
 const b=w.addWorksheet('別紙');b.getCell('A1').value='保持';
 const f=new Blob([await w.xlsx.writeBuffer()],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
 const out=await normalizeXlsxForExcel(f);
 assert.ok(out.size>0);
 const restored=new ExcelJS.Workbook();await restored.xlsx.load(await out.arrayBuffer());
 assert.deepEqual(restored.worksheets.map(x=>x.name),['売上','別紙']);
 assert.equal(restored.getWorksheet('売上').getCell('A2').value,'00001234');
 assert.equal(restored.getWorksheet('売上').getCell('C2').value.formula,'B2*2');
 assert.equal(restored.getWorksheet('別紙').getCell('A1').value,'保持');
});
test('invalid and too large blobs are rejected before saving',async()=>{
 await assert.rejects(normalizeXlsxForExcel(new Blob(['BAD'])),/XLSX出力/);
 await assert.rejects(normalizeXlsxForExcel(new Blob([new Uint8Array(50*1024*1024+1)])),/50MB/);
});
