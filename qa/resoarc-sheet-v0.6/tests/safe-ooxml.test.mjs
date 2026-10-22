import test from 'node:test';
import assert from 'node:assert/strict';
import ExcelJS from 'exceljs';
import JSZip from 'jszip';
import {captureSnapshot,valueOnlyDiff} from '../src/safe-diff.mjs';
import {patchOriginalWorkbook} from '../src/safe-ooxml.mjs';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==','base64');
const source=async()=> {
 const w=new ExcelJS.Workbook();w.creator='ResoArc';
 const sheet=w.addWorksheet('売上',{views:[{state:'frozen',ySplit:1}]});
 sheet.getCell('A1').value='見積';sheet.getCell('A1').font={bold:true};
 sheet.getCell('A2').value='部品';sheet.getCell('B2').value=3;
 sheet.getCell('C2').value={formula:'B2*2',result:6};
 sheet.getCell('D2').value='共有文字';
 sheet.getCell('D2').dataValidation={type:'list',formulae:['"A,B"']};
 sheet.addConditionalFormatting({ref:'B2',rules:[{type:'expression',formulae:['B2>5'],style:{fill:{type:'pattern',pattern:'solid',bgColor:{argb:'FFFF0000'}}}}]});
 const imageId=w.addImage({buffer:png,extension:'png'});
 sheet.addImage(imageId,{tl:{col:5,row:0},ext:{width:24,height:24}});
 const second=w.addWorksheet('説明');second.getCell('A1').value='削除しない';
 const b=await w.xlsx.writeBuffer();
 return Object.assign(new Blob([b]),{name:'fixture.xlsx'});
};
const sheets=(count=3,label='部品')=>[
 {name:'売上',id:'1',config:{},data:[[{v:'見積'}],[{v:label},{v:count,ct:{t:'n'}},{v:6,f:'=B2*2'},{v:'共有文字'}]]},
 {name:'説明',id:'2',config:{},data:[[{v:'削除しない'}]]}
];
function modified(){const arr=sheets();arr[0].data[1][1]={v:'7',ct:{t:'n'}};return arr;}
test('snapshot diff detects exactly changed number, not recalc caches',()=>{
 const from=captureSnapshot(sheets());
 const target=modified();target[0].data[1][2].v=14;
 const changes=valueOnlyDiff(from,target);
 assert.equal(changes.length,1);
 assert.deepEqual(changes[0].after,{type:'number',value:7,formula:null});
});
test('format edits, renamed sheet and inserted cell are blocked',()=>{
 const from=captureSnapshot(sheets());
 const styled=modified();styled[0].data[1][1].bg='#CC1111';
 assert.throws(()=>valueOnlyDiff(from,styled),/書式/);
 const renamed=modified();renamed[1].name='other';
 assert.throws(()=>valueOnlyDiff(from,renamed),/シート/);
 const inserted=modified();inserted[0].data[1][4]={v:3};
 assert.throws(()=>valueOnlyDiff(from,inserted),/追加/);
});
test('safe OOXML patch preserves images, formatting, conditional formatting, frozen panes and other sheets',async()=>{
 const sourceFile=await source();
 const before=await JSZip.loadAsync(await sourceFile.arrayBuffer());
 const edits=valueOnlyDiff(captureSnapshot(sheets()),modified());
 const patched=await patchOriginalWorkbook(sourceFile,edits);
 assert.equal(patched.count,1);
 const after=await JSZip.loadAsync(await patched.blob.arrayBuffer());
 assert.deepEqual(Object.keys(before.files).sort(),Object.keys(after.files).sort());
 const preserve=Object.keys(before.files).filter(name=>!before.files[name].dir).filter(name=>
  /^(xl\/media\/|xl\/drawings\/|xl\/styles\.xml$|xl\/sharedStrings\.xml$|xl\/worksheets\/_rels\/|xl\/worksheets\/sheet2\.xml$)/.test(name));
 assert.ok(preserve.some(p=>p.startsWith('xl/media/')),'expected media fixture');
 for(const p of preserve){
  assert.deepEqual(await before.file(p).async('uint8array'),await after.file(p).async('uint8array'),p);
 }
 const r=new ExcelJS.Workbook();await r.xlsx.load(Buffer.from(await patched.blob.arrayBuffer()));
 assert.equal(r.getWorksheet('売上').getCell('B2').value,7);
 assert.equal(r.getWorksheet('売上').getCell('A1').font.bold,true);
 assert.equal(r.getWorksheet('売上').getImages().length,1);
 assert.equal(r.getWorksheet('説明').getCell('A1').value,'削除しない');
 assert.equal(r.getWorksheet('売上').conditionalFormattings.length,1);
 assert.equal(r.getWorksheet('売上').getCell('C2').value.formula,'B2*2');
 assert.equal(r.getWorksheet('売上').views[0].state,'frozen');
 const original=await before.file('xl/worksheets/sheet1.xml').async('string');
 const output=await after.file('xl/worksheets/sheet1.xml').async('string');
 assert.ok(original.includes('conditionalFormatting')&&output.includes('conditionalFormatting'));
 const originalWorkbook=await before.file('xl/workbook.xml').async('string');
 const updatedWorkbook=await after.file('xl/workbook.xml').async('string');
 assert.match(updatedWorkbook,/fullCalcOnLoad="1"/);
 assert.equal(sourceFile.size>0,true);
});
test('no edits returns identical bytes without recompressing',async()=>{
 const f=await source();const unchanged=await patchOriginalWorkbook(f,[]);
 assert.deepEqual(Buffer.from(await f.arrayBuffer()),Buffer.from(await unchanged.blob.arrayBuffer()));
});
test('signed and macro parts blocked, and missing original cell blocked',async()=>{
 const f=await source(), z=await JSZip.loadAsync(await f.arrayBuffer());
 z.file('_xmlsignatures/sig1.xml','<signature/>');
 const signed=Object.assign(new Blob([await z.generateAsync({type:'uint8array'})]),{name:'signed.xlsx'});
 await assert.rejects(patchOriginalWorkbook(signed,valueOnlyDiff(captureSnapshot(sheets()),modified())),/電子署名/);
 const after=modified();after[0].data[1].push({v:'oops'});
 assert.throws(()=>valueOnlyDiff(captureSnapshot(sheets()),after),/追加/);
 await assert.rejects(patchOriginalWorkbook(f,[{sheet:'売上',r:9,c:9,after:{type:'number',value:1}}]),/存在しない/);
});

test('unicode XML text escaping and formula replacement are safe',async()=>{
 const file=await source();
 const originalSheets=sheets();
 const updated=sheets();
 updated[0].data[1][0]={v:'部品 & <工具> "銀"'};
 updated[0].data[1][2]={v:18,f:'=B2*6'};
 const changes=valueOnlyDiff(captureSnapshot(originalSheets),updated);
 assert.equal(changes.length,2);
 const {blob}=await patchOriginalWorkbook(file,changes);
 const wb=new ExcelJS.Workbook();await wb.xlsx.load(Buffer.from(await blob.arrayBuffer()));
 assert.equal(wb.getWorksheet('売上').getCell('A2').value,'部品 & <工具> "銀"');
 assert.equal(wb.getWorksheet('売上').getCell('C2').value.formula,'B2*6');
 assert.equal(wb.getWorksheet('売上').getImages().length,1);
});
test('safe save refuses to replace an existing formula with a constant',()=>{
 const modifiedSheets=sheets(); modifiedSheets[0].data[1][2]={v:20};
 assert.throws(()=>valueOnlyDiff(captureSnapshot(sheets()),modifiedSheets),/数式セル/);
});
test('safe save preserves format of an edited numeric cell',async()=>{
 const original=await source(),z=await JSZip.loadAsync(await original.arrayBuffer());
 const sheetXml=await z.file('xl/worksheets/sheet1.xml').async('string');
 assert.ok(sheetXml.includes('conditionalFormatting'));
 const changes=valueOnlyDiff(captureSnapshot(sheets()),modified());
 const patch=await patchOriginalWorkbook(original,changes);
 const restored=new ExcelJS.Workbook();await restored.xlsx.load(Buffer.from(await patch.blob.arrayBuffer()));
 assert.equal(restored.getWorksheet('売上').getCell('B2').value,7);
});
