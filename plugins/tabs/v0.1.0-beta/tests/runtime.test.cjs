const test=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../src/js/desktop.js'),'utf8');
function setup({config={tabs:JSON.stringify([{label:'基本',fields:['a','b']},{label:'詳細',fields:['c']}]),space:'resoarc_tabs'},mobile=false,hasSpace=true}={}){
 const handlers={},changes=[],children=[];
 function element(name){
  return {name,attrs:{},events:{},children:[],tabIndex:0,
   className:'',setAttribute(k,v){this.attrs[k]=v;},
   appendChild(x){this.children.push(x);},append(...xs){this.children.push(...xs);},
   addEventListener(type,fn){this.events[type]=fn;},remove(){this.removed=true;},
   focus(){this.focused=true;},querySelector(){return null}};
 }
 const space={querySelector:()=>null,appendChild(x){children.push(x)}};
 const recApi={getSpaceElement:(id)=>id==='resoarc_tabs'&&hasSpace?space:null,setFieldShown:(field,shown)=>changes.push({field,shown})};
 const kintone={$PLUGIN_ID:'alpha',plugin:{app:{getConfig:()=>config}},events:{on(types,fn){for(const t of types)handlers[t]=fn}},
 app:{record:recApi},mobile:{app:{record:recApi}}};
 const ctx={kintone,document:{createElement:element},console};
 ctx.globalThis=ctx;
 vm.runInNewContext(code,ctx);
 function show(type='app.record.create.show'){const event={type,record:{}};return handlers[type](event);}
 return {handlers,changes,children,show};
}
function own(value){return JSON.parse(JSON.stringify(value));}
test('creates tabs using supported field show API',()=>{
 const x=setup(),event=x.show();
 assert.equal(event.type,'app.record.create.show');
 assert.equal(x.children.length,1);
 assert.deepEqual(own(x.changes),[{field:'a',shown:true},{field:'b',shown:true},{field:'c',shown:false}]);
 const tabs=x.children[0].children;
 tabs[1].events.click();
 assert.deepEqual(own(x.changes.slice(-3)),[{field:'a',shown:false},{field:'b',shown:false},{field:'c',shown:true}]);
 assert.equal(tabs[1].attrs['aria-selected'],'true');
});
test('show all restores targeted fields, preserving unrelated fields',()=>{
 const x=setup();x.show();const bar=x.children[0];
 bar.children[2].events.click();
 assert.deepEqual(own(x.changes.slice(-3)),[{field:'a',shown:true},{field:'b',shown:true},{field:'c',shown:true}]);
});
test('save hook restores visibility before save and returns event',()=>{
 const x=setup(),e={type:'app.record.edit.submit',record:{}};
 assert.equal(x.handlers[e.type](e),e);
 assert.deepEqual(own(x.changes),[{field:'a',shown:true},{field:'b',shown:true},{field:'c',shown:true}]);
});
test('mobile record events select the mobile API',()=>{
 const x=setup({mobile:true});
 x.show('mobile.app.record.detail.show');
 assert.equal(x.children.length,1);
});
test('missing space leaves the record unmodified',()=>{
 const x=setup({hasSpace:false}),e=x.show();
 assert.equal(x.children.length,0);assert.equal(x.changes.length,0);assert.equal(e.type,'app.record.create.show');
});
test('invalid config produces no event handlers',()=>{
 const x=setup({config:{tabs:'not-json'}});
 assert.equal(Object.keys(x.handlers).length,0);
});
test('arrow key switches tab while preserving accessible roles',()=>{
 const x=setup();x.show();const buttons=x.children[0].children;
 let prevent=false;buttons[0].events.keydown({key:'ArrowRight',preventDefault(){prevent=true}});
 assert.equal(prevent,true);
 assert.equal(buttons[1].attrs['aria-selected'],'true');
 assert.equal(buttons[1].focused,true);
});
