const test=require('node:test');
const assert=require('node:assert/strict');
const core=require('../src/js/core.js');
const cfg={field:'line_no',table:'items',prefix:'RA-',width:'6',start:'1'};
function record(rows){
 return {$revision:{value:'4'},items:{type:'SUBTABLE',value:rows.map(([id,value,name])=>({
  id:String(id),value:{line_no:{type:'SINGLE_LINE_TEXT',value},description:{type:'SINGLE_LINE_TEXT',value:name}}
 }))}};
}
test('table numbering follows immutable record ID and row ID',()=>{
 assert.equal(core.makeRowNumber('31','9',cfg),'RA-000031-9');
 assert.equal(core.makeRowNumber('31','12345',cfg),'RA-000031-12345');
 assert.notEqual(core.makeRowNumber('31','4',cfg),core.makeRowNumber('31','5',cfg));
});
test('table update preserves every row and non-target cells by omission',()=>{
 const plan=core.planUpdate('31',record([['9','','A'],['12','RA-000031-12','B'],['20','','C']]),cfg);
 assert.equal(plan.updated,true);
 assert.equal(plan.record.items.value.length,3);
 assert.deepEqual(plan.record.items.value.map(x=>x.id),['9','12','20']);
 assert.deepEqual(plan.record.items.value[0].value,{line_no:{value:'RA-000031-9'}});
 assert.equal('value' in plan.record.items.value[1],false);
 assert.deepEqual(plan.record.items.value[2].value,{line_no:{value:'RA-000031-20'}});
 assert.equal(JSON.stringify(plan.record).includes('description'),false);
});
test('existing numbering remains stable after reorder',()=>{
 const first=core.planUpdate('31',record([['100','','A'],['300','','B']]),cfg);
 assert.deepEqual(first.numbers,['RA-000031-100','RA-000031-300']);
 const next=core.planUpdate('31',record([['300','RA-000031-300','B'],['100','RA-000031-100','A']]),cfg);
 assert.equal(next.updated,false);
 assert.deepEqual(next.numbers,['RA-000031-300','RA-000031-100']);
});
test('new row after edit gets numbered without overwriting existing',()=>{
 const p=core.planUpdate('31',record([['100','RA-000031-100','A'],['301','','C']]),cfg);
 assert.equal(p.updated,true);assert.deepEqual(p.numbers,['RA-000031-100','RA-000031-301']);
});
test('deleted row ID is never used for a new row',()=>{
 assert.notEqual(core.makeRowNumber('31','42',cfg),core.makeRowNumber('31','44',cfg));
});
test('read-only and incomplete configurations fail safely',()=>{
 assert.equal(core.validConfig({...cfg,table:'line_no'}),null);
 assert.throws(()=>core.planUpdate('31',{},cfg),/テーブル/);
 assert.throws(()=>core.planUpdate('31',record([['', '', 'A']]),cfg),/行ID/);
 assert.throws(()=>core.makeRowNumber('31','new-row',cfg),/行ID/);
});
test('pre-existing duplicate numbers halt update instead of silently leaving duplicates',()=>{
 assert.throws(()=>core.planUpdate('31',record([['9','X','A'],['10','X','B']]),cfg),/重複/);
});
test('row ID uniqueness without truncation at high precision',()=>{
 assert.equal(core.makeRowNumber('9007199254740993','9007199254740994',{...cfg,prefix:''}), '9007199254740993-9007199254740994');
});
