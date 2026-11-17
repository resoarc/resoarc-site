import test from 'node:test';
import assert from 'node:assert/strict';
import JSZip from 'jszip';
import {inspectXlsx,auditExcelSave,formatAuditMessage} from '../src/compat-audit.mjs';

async function workbook({advanced=false}={}){
 const zip=new JSZip();
 zip.file('xl/workbook.xml',advanced?'<workbook><definedNames><definedName name="Important">Sheet1!A1</definedName></definedNames></workbook>':'<workbook/>');
 zip.file('xl/worksheets/sheet1.xml',advanced?
   '<worksheet><sheetViews><sheetView><pane state="frozen"/></sheetView></sheetViews><mergeCells><mergeCell ref="A1:B1"/></mergeCells><conditionalFormatting sqref="A2"><cfRule type="expression" priority="1"/></conditionalFormatting><dataValidations><dataValidation type="list" sqref="B2"/></dataValidations><hyperlinks><hyperlink ref="A3" r:id="rId1"/></hyperlinks></worksheet>':
   '<worksheet><sheetData><row r="1"><c r="A1" t="n"><v>5</v></c></row></sheetData></worksheet>');
 if(advanced){zip.file('xl/charts/chart1.xml','<chart/>');zip.file('xl/drawings/drawing1.xml','<drawing/>');zip.file('xl/media/image1.png','image');}
 const blob=await zip.generateAsync({type:'blob'});
 return Object.assign(blob,{name:'sample.xlsx'});
}
test('plain workbook has no advanced risks',async()=>{
 const report=await inspectXlsx(await workbook());
 assert.deepEqual(report.features,[]);
 assert.equal(report.totalParts,2);
});
test('detects structural losses across OOXML packages',async()=>{
 const report=await auditExcelSave(await workbook({advanced:true}),await workbook());
 const ids=report.losses.map(x=>x.id);
 for(const id of ['charts','drawings','images','definedNames','conditional','validation','merged','freeze','hyperlinks'])
  assert.ok(ids.includes(id),id);
 assert.match(formatAuditMessage(report),/グラフ/);
 assert.equal(report.hasRisks,true);
});
test('unchanged structures do not appear as losses',async()=>{
 const blob=await workbook({advanced:true});
 const report=await auditExcelSave(blob,blob);
 assert.deepEqual(report.losses,[]);
 assert.equal(report.hasRisks,true);
});

test('chart under xl/drawings/charts is detected as an advanced Excel feature',async()=>{
 const zip=new JSZip();
 zip.file('xl/workbook.xml','<workbook/>');
 zip.file('xl/drawings/charts/chart1.xml','<chart/>');
 const f=Object.assign(new Blob([await zip.generateAsync({type:'uint8array'})]),{name:'nested.xlsx'});
 const r=await inspectXlsx(f);
 assert.equal(r.features.find(x=>x.id==='charts')?.count,1);
});
test('large worksheet XML up to 16MB can be audited without truncation',async()=>{
 const zip=new JSZip();
 zip.file('xl/workbook.xml','<workbook/>');
 zip.file('xl/worksheets/sheet1.xml','<worksheet>'+(' '.repeat(10*1024*1024))+'</worksheet>');
 const data=await zip.generateAsync({type:'blob'});
 const f=Object.assign(data,{name:'large.xlsx'});
 const report=await inspectXlsx(f);
 assert.equal(report.totalParts,2);
});
test('oversized single XML exceeding 16MB is rejected',async()=>{
 const zip=new JSZip();
 zip.file('xl/workbook.xml','<workbook/>');
 zip.file('xl/worksheets/sheet1.xml','<worksheet>'+(' '.repeat(16*1024*1024+256))+'</worksheet>');
 const f=Object.assign(await zip.generateAsync({type:'blob'}),{name:'oversized.xlsx'});
 await assert.rejects(()=>inspectXlsx(f),/内部XMLが大きすぎる/);
});
