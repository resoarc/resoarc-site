const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const code=fs.readFileSync(path.resolve(__dirname,'../src/js/desktop.js'),'utf8');
function init({source='status',target='reason',required=true,operator='eq',value='NG'}={}){
 const events={},visibility=[];
 const rules=[{source,target,operator,value,required}];
 const api={setFieldShown:(f,b)=>visibility.push([f,b])};
 const kintone={$PLUGIN_ID:'x',plugin:{app:{getConfig:()=>({rules:JSON.stringify(rules)})}},
 events:{on(keys,fn){for(const key of keys)events[key]=fn;}},app:{record:api},mobile:{app:{record:api}}};
 const ctx={kintone,console};ctx.globalThis=ctx;
 vm.runInNewContext(code,ctx);
 return {events,visibility,api};
}
test('missing source must block saving rather than bypass required',()=>{
 const {events}=init(),event={type:'app.record.edit.submit',record:{reason:{value:''}}};
 events[event.type](event);
 assert.match(event.error,/対象フィールド/);
});
test('missing target must block saving',()=>{
 const {events}=init(),event={type:'app.record.create.submit',record:{status:{value:'NG'}}};
 events[event.type](event);
 assert.match(event.error,/対象フィールド/);
});
test('required target becomes visible when validation fails',()=>{
 const {events,visibility}=init();
 const event={type:'app.record.create.submit',record:{status:{value:'NG'},reason:{value:''}}};
 events[event.type](event);
 assert.equal(event.record.reason.error,'この条件では入力が必要です。');
 assert.deepEqual(visibility,[['reason',true]]);
});
test('unrelated validation error remains intact',()=>{
 const {events}=init();
 const event={type:'mobile.app.record.edit.submit',record:{status:{value:'OK'},reason:{value:'',error:'Other plugin validation'}}};
 events[event.type](event);
 assert.equal(event.record.reason.error,'Other plugin validation');
});
test('when condition clears, plugin error is cleared without deleting value',()=>{
 const {events}=init();
 const event={type:'app.record.edit.submit',record:{status:{value:'OK'},reason:{value:'retained',error:'この条件では入力が必要です。'}}};
 events[event.type](event);
 assert.equal(event.record.reason.value,'retained');
 assert.equal(event.record.reason.error,null);
});
test('visibility API failure is not a validation bypass',()=>{
 const {events,api}=init();
 api.setFieldShown=()=>{throw Error('could not show field')};
 const event={type:'app.record.create.submit',record:{status:{value:'NG'},reason:{value:''}}};
 events[event.type](event);
 assert.match(event.error,/チェックを完了/);
});
test('change event reads condition and does not modify hidden data',()=>{
 const {events,visibility}=init();
 const event={type:'mobile.app.record.edit.change.status',record:{status:{value:'OK'},reason:{value:'keep'}}};
 assert.equal(events[event.type](event),event);
 assert.deepEqual(visibility,[['reason',false]]);
 assert.equal(event.record.reason.value,'keep');
});
