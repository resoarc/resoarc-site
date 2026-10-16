const test=require('node:test'),a=require('node:assert/strict'),core=require('../src/js/core.js');
const rows=[{$id:{value:'12'},$revision:{value:'2'},Name:{type:'SINGLE_LINE_TEXT',value:'Old'}},{$id:{value:'13'},$revision:{value:'3'},Name:{type:'SINGLE_LINE_TEXT',value:'Nochange'}}];
test('grid config supports only one field',()=>a.deepEqual(core.normalize([{field:'Name'}]),{field:'Name',limit:30}));
test('grid rejects multiple target configs',()=>a.equal(core.normalize([{field:'a'},{field:'b'}]),null));
test('grid preview includes revision for optimistic concurrency',()=>{const p=core.preview(rows,'Name',{'12':'New'});a.equal(p.changedCount,1);a.equal(p.changes[0].revision,'2');a.equal(p.changes[0].id,'12');});
test('grid unchanged input is ignored',()=>a.equal(core.preview(rows,'Name',{'12':'Old'}).changedCount,0));
test('grid does not mutate source',()=>{core.preview(rows,'Name',{'12':'New'});a.equal(rows[0].Name.value,'Old');});
test('grid fails closed without revision',()=>a.throws(()=>core.preview([{$id:{value:'12'},Name:{type:'SINGLE_LINE_TEXT',value:'x'}}],'Name',{'12':'y'})));
test('grid fails closed for complex object value',()=>a.throws(()=>core.preview([{$id:{value:'12'},$revision:{value:'1'},Name:{type:'SINGLE_LINE_TEXT',value:[1]}}],'Name',{'12':'x'})));
test('grid refuses auto-calculated and date fields',()=>{
 for(const type of ['CALC','DATE','STATUS','CREATED_TIME','FILE']){
  a.equal(core.canEdit({type,value:'2026-01-01'}),false,type);
 }
});
test('grid accepts supported text and number types',()=>{
 for(const type of core.EDITABLE_TYPES)a.equal(core.canEdit({type,value:'12'}),true);
});
test('grid refuses nonnumeric update before API call',()=>{
 const rec={$id:{value:'1'},$revision:{value:'1'},Number:{type:'NUMBER',value:'10'}};
 a.throws(()=>core.preview([rec],'Number',{'1':'10,000'}),/半角数字/);
 a.throws(()=>core.preview([rec],'Number',{'1':'Infinity'}),/半角数字/);
 a.equal(core.preview([rec],'Number',{'1':'-1.25'}).changedCount,1);
});
test('grid text length limited',()=>a.throws(()=>core.validateValue({type:'SINGLE_LINE_TEXT'},'x'.repeat(5001)),/5,000/));
test('grid unsupported type has no write preview',()=>{
 const rec={$id:{value:'1'},$revision:{value:'1'},Date:{type:'DATE',value:'2026-01-01'}};
 a.throws(()=>core.preview([rec],'Date',{'1':'2026-02-01'}),/更新可能/);
});
