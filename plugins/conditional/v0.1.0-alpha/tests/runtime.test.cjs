const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const src=fs.readFileSync(path.resolve(__dirname,'../src/js/desktop.js'),'utf8');
const rules=[{source:'status',target:'reason',operator:'eq',value:'NG',required:true}];
function make(config={rules:JSON.stringify(rules)}){
 const handlers={},changes=[];
 const api={setFieldShown:(field,shown)=>changes.push({field,shown})};
 const kintone={$PLUGIN_ID:'test',plugin:{app:{getConfig:()=>config}},events:{on(events,fn){for(const e of events)handlers[e]=fn}},
 app:{record:api},mobile:{app:{record:api}}};
 const ctx={kintone,console};ctx.globalThis=ctx;vm.runInNewContext(src,ctx);
 return {handlers,changes};
}
function own(x){return JSON.parse(JSON.stringify(x))}
test('show and change adjust targeted visibility',()=>{
 const m=make(),e={type:'app.record.create.show',record:{status:{value:'OK'},reason:{value:'original'}}};
 assert.equal(m.handlers[e.type](e),e);
 assert.deepEqual(own(m.changes),[{field:'reason',shown:false}]);
 e.record.status.value='NG';
 m.handlers['app.record.create.change.status']({...e,type:'app.record.create.change.status'});
 assert.deepEqual(own(m.changes.slice(-1)),[{field:'reason',shown:true}]);
 assert.equal(e.record.reason.value,'original');
});
test('active condition requires reason on save',()=>{
 const m=make();const e={type:'app.record.create.submit',record:{status:{value:'NG'},reason:{value:''}}};
 const result=m.handlers[e.type](e);
 assert.equal(result,e);
 assert.equal(e.record.reason.error,'この条件では入力が必要です。');
});
test('inactive condition does not prevent save or erase hidden values',()=>{
 const m=make();const e={type:'app.record.edit.submit',record:{status:{value:'OK'},reason:{value:'keep'}}};
 m.handlers[e.type](e);
 assert.equal(e.record.reason.error,undefined);
 assert.equal(e.record.reason.value,'keep');
});
test('switching condition off removes only plugin own error',()=>{
 const m=make();const e={type:'app.record.edit.submit',record:{status:{value:'NG'},reason:{value:''}}};
 m.handlers[e.type](e);
 e.record.status.value='OK';
 m.handlers[e.type](e);
 assert.equal(e.record.reason.error,null);
});
test('missing driver does not hide or fail the record',()=>{
 const m=make();const e={type:'app.record.detail.show',record:{reason:{value:''}}};
 m.handlers[e.type](e);
 assert.equal(m.changes.length,0);
});
test('mobile hooks are registered',()=>{
 const m=make();const e={type:'mobile.app.record.create.submit',record:{status:{value:'NG'},reason:{value:null}}};
 m.handlers[e.type](e);
 assert.equal(e.record.reason.error,'この条件では入力が必要です。');
});
test('invalid config activates no handlers',()=>{
 const m=make({rules:'garbled'});
 assert.equal(Object.keys(m.handlers).length,0);
});
