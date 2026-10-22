import test from 'node:test';
import assert from 'node:assert/strict';
import {scanWorkbook} from '../src/preflight.mjs';
test('unsupported file rejection',async()=>{const f=Object.assign(new Blob(['example']),{name:'example.unknown'});await assert.rejects(scanWorkbook(f));});
test('CSV can be opened',async()=>{const f=Object.assign(new Blob(['a,b']),{name:'sample.csv'});assert.deepEqual(await scanWorkbook(f),[]);});
test('legacy workbook is blocked',async()=>{const f=Object.assign(new Blob(['legacy']),{name:'sample.xls'});await assert.rejects(scanWorkbook(f),/安全に保存/);});
import JSZip from 'jszip';
test('warn on chart content',async()=>{
 const zip=new JSZip();zip.file('xl/workbook.xml','<workbook/>');zip.file('xl/charts/chart1.xml','chart');
 const data=await zip.generateAsync({type:'uint8array'});
 const f=Object.assign(data,{name:'chart.xlsx',size:data.byteLength});
 assert.deepEqual(await scanWorkbook(f),['グラフを含みます']);
});
test('xlsm and xlsb are always blocked',async()=>{
 for(const ext of ['xlsm','xlsb']){
  const f=Object.assign(new Blob(['no']),{name:'macro.'+ext});
  await assert.rejects(scanWorkbook(f),/安全に保存/);
 }
});
test('too large file is blocked',async()=>{
 const f=Object.assign(new Blob([new Uint8Array(20*1024*1024+1)]),{name:'large.xlsx'});
 await assert.rejects(scanWorkbook(f),/20MB/);
});
test('non workbook zip is blocked',async()=>{
 const z=new JSZip();z.file('word/document.xml','example');
 const content=await z.generateAsync({type:'uint8array'});
 const f=Object.assign(content,{name:'not-xlsx.xlsx',size:content.byteLength});
 await assert.rejects(scanWorkbook(f),/正しい/);
});