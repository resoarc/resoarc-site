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

test('grid atomic update payload includes all records and revisions in one request',()=>{
 const plan=core.preview(rows,'Name',{'12':'Next','13':'Final'});
 const request=core.batchRequest(plan,42);
 a.equal(request.app,42);
 a.equal(request.records.length,2);
 a.equal(request.records[0].id,'12');
 a.equal(request.records[0].revision,'2');
 a.deepEqual(request.records[0].record,{Name:{value:'Next'}});
 a.equal(request.records[1].revision,'3');
});
test('grid atomic request forbids >100 and empty plans',()=>{
 const one=core.preview(rows,'Name',{'12':'Next'});
 a.throws(()=>core.batchRequest({...one,changedCount:0,changes:[]},42),/1～100/);
 a.throws(()=>core.batchRequest({...one,changedCount:101,changes:Array.from({length:101},()=>one.changes[0])},42),/1～100/);
});
test('grid atomic request rejects tampered plan and duplicate IDs',()=>{
 const plan=core.preview(rows,'Name',{'12':'Next','13':'Final'});
 a.throws(()=>core.batchRequest({...plan,changes:[plan.changes[0],plan.changes[0]]},42),/不正/);
 a.throws(()=>core.batchRequest({...plan,changes:[{...plan.changes[0],field:'Else'},plan.changes[1]]},42),/不正/);
 a.throws(()=>core.batchRequest(plan,'bad'),/アプリ/);
});

test('grid preflight only reads target record IDs, revision and field',()=>{
 const plan=core.preview(rows,'Name',{'12':'Next','13':'Final'});
 const query=core.preflightRequest(plan,42);
 a.deepEqual(query,{app:42,fields:['$id','$revision','Name'],query:'$id in (12,13) limit 2'});
});
test('grid GET preflight accepts unchanged records',()=>{
 const plan=core.preview(rows,'Name',{'12':'Next','13':'Final'});
 const outgoing=core.confirmUnchanged(plan,{records:[rows[1],rows[0]]},42);
 a.equal(outgoing.records.length,2);
 a.equal(outgoing.records[0].revision,'2');
});
test('grid GET preflight refuses stale revision and changed source',()=>{
 const plan=core.preview(rows,'Name',{'12':'Next','13':'Final'});
 const stale=[{...rows[0],$revision:{value:'99'}},rows[1]];
 a.throws(()=>core.confirmUnchanged(plan,{records:stale},42),/変更されています/);
 const tampered=[{...rows[0],Name:{type:'SINGLE_LINE_TEXT',value:'Changed remotely'}},rows[1]];
 a.throws(()=>core.confirmUnchanged(plan,{records:tampered},42),/変更されています/);
});
test('grid GET preflight rejects missing, extra and duplicate data, no PUT allowed',()=>{
 const plan=core.preview(rows,'Name',{'12':'Next','13':'Final'});
 a.throws(()=>core.confirmUnchanged(plan,{records:[rows[0]]},42),/取得件数/);
 a.throws(()=>core.confirmUnchanged(plan,{records:[rows[0],rows[0]]},42),/レコードID/);
 a.throws(()=>core.confirmUnchanged(plan,{records:[rows[0],{$id:{value:'99'},$revision:{value:'1'},Name:{type:'SINGLE_LINE_TEXT',value:'Something'}}]},42),/見つかりません/);
 a.throws(()=>core.confirmUnchanged(plan,{records:[rows[0],{...rows[1],Name:{type:'DATE',value:'2026-10-16'}}]},42),/変更されています/);
});
