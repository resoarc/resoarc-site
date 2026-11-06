const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/js/desktop.js'),'utf8');
const cfg={field:'line_no',table:'items',prefix:'RA-',width:'6',start:'1'};
function mk(){
 const handlers={},calls=[];
 let revision=4;
 const rows=[
 {id:'8',value:{line_no:{type:'SINGLE_LINE_TEXT',value:''},name:{type:'SINGLE_LINE_TEXT',value:'Do not delete'}}},
 {id:'12',value:{line_no:{type:'SINGLE_LINE_TEXT',value:'RA-000031-12'},name:{type:'SINGLE_LINE_TEXT',value:'Retain'}}}
 ];
 const api=async (_,method,args)=>{
  calls.push({method,args});
  if(method==='GET'){
   return {record:{$revision:{value:String(revision)},items:{type:'SUBTABLE',value:JSON.parse(JSON.stringify(rows))}}};
  }
  if(method==='PUT'){
   assert.equal(args.revision,String(revision));
   assert.equal(args.record.items.value.length,rows.length);
   for(const r of args.record.items.value){
    const target=rows.find(x=>x.id===r.id);
    assert.ok(target,'Never append duplicate or delete a row');
    if(r.value?.line_no)target.value.line_no.value=r.value.line_no.value;
   }
   revision++;
   return {revision:String(revision)};
  }
 };
 api.url=u=>u;
 const kintone={$PLUGIN_ID:'test',plugin:{app:{getConfig:()=>cfg}},events:{on(types,fn){for(const type of types)handlers[type]=fn}},api,app:{record:{getHeaderMenuSpaceElement:()=>null}}};
 const window={__RESOARC_TEST__:{},alert:()=>{},location:{reload(){}}};
 const ctx={kintone,window,console};
 ctx.globalThis=ctx;
 vm.runInNewContext(source,ctx);
 return {handlers,calls,rows,window};
}
test('saved event updates only missing row field, maintaining every row',async()=>{
 const m=mk();
 const ev={appId:48,recordId:'31',record:{},type:'app.record.create.submit.success'};
 await m.handlers[ev.type](ev);
 assert.deepEqual(m.calls.map(c=>c.method),['GET','PUT']);
 assert.equal(m.rows[0].value.line_no.value,'RA-000031-8');
 assert.equal(m.rows[1].value.line_no.value,'RA-000031-12');
 assert.equal(m.rows[0].value.name.value,'Do not delete');
 await m.handlers[ev.type](ev);
 assert.deepEqual(m.calls.map(c=>c.method),['GET','PUT','GET']);
});
test('editing the record triggers fill, new row updates too',async()=>{
 const m=mk();
 const ev={appId:48,recordId:'31',type:'app.record.edit.submit.success'};
 await m.handlers[ev.type](ev);
 assert.equal(m.rows[0].value.line_no.value,'RA-000031-8');
});
test('pre-save create blanks row numbers, edit never clears them',()=>{
 const m=mk();
 const original={items:{type:'SUBTABLE',value:[{id:'8',value:{line_no:{value:'before',disabled:false}}}]}};
 const ev={type:'app.record.create.show',record:original};
 m.handlers[ev.type](ev);
 assert.equal(original.items.value[0].value.line_no.value,'');
 assert.equal(original.items.value[0].value.line_no.disabled,true);
 original.items.value[0].value.line_no.value='existing';
 m.handlers['app.record.edit.show']({type:'app.record.edit.show',record:original});
 assert.equal(original.items.value[0].value.line_no.value,'existing');
});
