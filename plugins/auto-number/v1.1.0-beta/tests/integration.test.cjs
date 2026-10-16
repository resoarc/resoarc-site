const test=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const script=fs.readFileSync(path.resolve(__dirname,'../src/js/desktop.js'),'utf8');
function mock(config,initial=''){
  const handlers={}, calls=[], records=new Map([['31',{number:{value:initial},$revision:{value:'1'}}]]);
  const api=async(url,method,params)=>{
    calls.push({method,params});
    if(method==='GET'){const r=records.get(String(params.id));return {record:JSON.parse(JSON.stringify(r))};}
    if(method==='PUT'){
      const r=records.get(String(params.id));
      if(params.revision!==r.$revision.value)throw new Error('revision mismatch');
      r.number.value=params.record.number.value;r.$revision.value=String(Number(r.$revision.value)+1);return {revision:r.$revision.value};
    }
  };api.url=x=>x;
  const banner={nodes:[],querySelector:()=>null,appendChild(x){this.nodes.push(x);}};
  const document={createElement:(name)=>({tagName:name,children:[],className:'',dataset:{},setAttribute(){},append(...xs){this.children.push(...xs)},appendChild(x){this.children.push(x)},remove(){this.removed=true},addEventListener(event,fn){this.handlers=this.handlers||{};this.handlers[event]=fn;}})};
  const context={kintone:{$PLUGIN_ID:'plugin-test',plugin:{app:{getConfig(){return config;}}},events:{on(types,cb){for(const type of types)handlers[type]=cb}},api,app:{record:{getHeaderMenuSpaceElement:()=>banner}}},document,window:{alert(){},location:{reload() {}}},console};
  context.globalThis=context;
  vm.runInNewContext(script,context);
  return {handlers,calls,records,banner,context};
}
test('create after save assigns record-ID derived value and no overwrite',async()=>{
 const m=mock({field:'number',prefix:'INV-',width:'6',start:'1'});
 const e={appId:12,recordId:'31',record:{number:{value:''}},type:'app.record.create.submit.success'};
 const ret=await m.handlers[e.type](e);
 assert.equal(ret,e);assert.equal(m.records.get('31').number.value,'INV-000031');
 assert.deepEqual(m.calls.map(c=>c.method),['GET','PUT']);
 await m.handlers[e.type](e);
 assert.deepEqual(m.calls.map(c=>c.method),['GET','PUT','GET']);
});
test('creation and edit do not allow human changes of target',()=>{
 const m=mock({field:'number',prefix:'',width:'6',start:'1'});
 let e={type:'app.record.create.show',record:{number:{value:'arbitrary',disabled:false}}};
 m.handlers[e.type](e);
 assert.equal(e.record.number.value,'');assert.equal(e.record.number.disabled,true);
 e={type:'app.record.edit.show',record:{number:{value:'INV-1',disabled:false}}};
 m.handlers[e.type](e);
 assert.equal(e.record.number.value,'INV-1');assert.equal(e.record.number.disabled,true);
});
test('mobile create supported and missing field safe',async()=>{
 const m=mock({field:'number',prefix:'',width:'6',start:'1'});
 const show={record:{other:{value:'x'}},type:'mobile.app.record.create.show'};
 assert.equal(m.handlers[show.type](show),show);
 await m.handlers['mobile.app.record.create.submit.success']({appId:12,recordId:'31',type:'mobile.app.record.create.submit.success'});
 assert.equal(m.records.get('31').number.value,'000031');
});
test('failed API never reports saved record as unsaved',async()=>{
 const m=mock({field:'number',prefix:'',width:'6',start:'1'});
 const failure=async()=>{throw Error('no permission')};failure.url=(x)=>x;m.context.kintone.api=failure;
 let shown=[];m.context.window.alert=(x)=>shown.push(x);
 const e={appId:12,recordId:'31',type:'app.record.create.submit.success'};
 const ret=await m.handlers[e.type](e);
 assert.equal(ret,e);assert.equal(shown.length,1);
 assert.ok(shown[0].includes('保存されましたが'));
});
test('bad configuration registers no event handlers',()=>{
 const m=mock({field:'',prefix:'',width:'6',start:'1'});
 assert.equal(Object.keys(m.handlers).length,0);
});
