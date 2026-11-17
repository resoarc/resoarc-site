import test from 'node:test';
import assert from 'node:assert/strict';
import {decideNormalXlsxSave} from '../src/xlsx-save-policy.mjs';

test('a new workbook may be exported without a source',()=>{
 assert.deepEqual(decideNormalXlsxSave(null),{action:'allow',lost:[]});
 assert.deepEqual(decideNormalXlsxSave({hasRisks:false,losses:[]}),{action:'allow',lost:[]});
});
test('a workbook with advanced features but no measured loss needs confirmation',()=>{
 assert.equal(decideNormalXlsxSave({hasRisks:true,losses:[]}).action,'confirm');
});
test('lossy export is blocked by default, without explicit format choice and consent',()=>{
 const a={hasRisks:true,losses:[{id:'charts',label:'グラフ',missing:1},{id:'images',label:'画像',missing:1}]};
 assert.equal(decideNormalXlsxSave(a).action,'block');
 assert.equal(decideNormalXlsxSave(a,{acceptLoss:false}).action,'block');
 assert.deepEqual(decideNormalXlsxSave(a).lost.map(x=>x.id),['charts','images']);
});
test('explicit simplified-XLSX consent permits a second, precise loss confirmation',()=>{
 const a={hasRisks:true,losses:[{id:'charts',label:'グラフ',missing:1},{id:'images',label:'画像',missing:1}]};
 const d=decideNormalXlsxSave(a,{acceptLoss:true});
 assert.equal(d.action,'confirm-loss');
 assert.deepEqual(d.lost.map(x=>x.id),['charts','images']);
});
test('zero missing features never triggers destructive export confirmation',()=>{
 assert.equal(decideNormalXlsxSave({hasRisks:true,losses:[{id:'images',missing:0}]},{acceptLoss:true}).action,'confirm');
});
test('medium severity losses need explicit consent too',()=>{
 const a={hasRisks:false,losses:[{id:'freeze',label:'ウィンドウ固定',missing:1}]};
 assert.equal(decideNormalXlsxSave(a).action,'block');
 assert.equal(decideNormalXlsxSave(a,{acceptLoss:true}).action,'confirm-loss');
});
