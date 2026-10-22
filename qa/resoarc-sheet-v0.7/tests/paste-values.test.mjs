import test from 'node:test';
import assert from 'node:assert/strict';
import {parseTsv,asPasteValue,validatePaste} from '../src/paste-values.mjs';
test('tab separated spreadsheet matrix and numeric types',()=>{
 const p=validatePaste('品名\t数量\r\n鉛筆\t12\r\nノート\t0007\r\n');
 assert.deepEqual(p.data,[['品名','数量'],['鉛筆',12],['ノート','0007']]);
 assert.equal(p.cellCount,6);
});
test('quoted tab and newline cells',()=>{
 assert.deepEqual(parseTsv('"A\tB"\t5\n"二行\n目"\t-1.25'),[['A\tB','5'],['二行\n目','-1.25']]);
});
test('formula-like pasted values are rejected',()=>{
 assert.throws(()=>validatePaste('ok\t=2+2'),/数式/);
});
test('excessive cells and invalid quoting are rejected',()=>{
 assert.throws(()=>validatePaste('1\t2\n3\t4',{maxCells:3}),/セル数/);
 assert.throws(()=>parseTsv('"not closed'),/引用符/);
});
test('numeric parsing avoids precision loss and preserves text',()=>{
 assert.equal(asPasteValue('0007'),'0007');
 assert.equal(asPasteValue('-4.25'),-4.25);
 assert.equal(asPasteValue('9007199254740993'),'9007199254740993');
 assert.equal(asPasteValue('0'),0);
});
