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