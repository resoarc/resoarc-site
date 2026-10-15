const test=require('node:test'),a=require('node:assert/strict'),core=require('../src/js/core.js');
const rows=[{$id:{value:'12'},$revision:{value:'2'},Name:{value:'Old'}},{$id:{value:'13'},$revision:{value:'3'},Name:{value:'Nochange'}}];
test('grid config supports only one field',()=>a.deepEqual(core.normalize([{field:'Name'}]),{field:'Name',limit:30}));
test('grid rejects multiple target configs',()=>a.equal(core.normalize([{field:'a'},{field:'b'}]),null));
test('grid preview includes revision for optimistic concurrency',()=>{const p=core.preview(rows,'Name',{'12':'New'});a.equal(p.changedCount,1);a.equal(p.changes[0].revision,'2');a.equal(p.changes[0].id,'12');});
test('grid unchanged input is ignored',()=>a.equal(core.preview(rows,'Name',{'12':'Old'}).changedCount,0));
test('grid does not mutate source',()=>{core.preview(rows,'Name',{'12':'New'});a.equal(rows[0].Name.value,'Old');});
test('grid fails closed without revision',()=>a.throws(()=>core.preview([{$id:{value:'12'},Name:{value:'x'}}],'Name',{'12':'y'})));
test('grid fails closed for complex object value',()=>a.throws(()=>core.preview([{$id:{value:'12'},$revision:{value:'1'},Name:{value:[1]}}],'Name',{'12':'x'})));
