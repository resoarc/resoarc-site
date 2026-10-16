const fs=require('fs'),path=require('path'),vm=require('vm');
const test=require('node:test'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const catalog=JSON.parse(fs.readFileSync(path.join(root,'catalog.json'),'utf8'));
const supported=new Set(['attachment-count','barcode-scan','csv-export','field-help','file-preview',
'input-template','list-aggregate','lookup-suggest','mail-compose','postal-address','qr-code',
'record-toc','related-links','reuse-reset','table-row-tools','text-normalizer']);
class Element {
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.style={};this.listeners={};
    this.value='';this.selectedIndex=0;this.id='';this.textContent='';this.dataset={};this.href='';this.type='';this.className='';}
  append(...a){this.children.push(...a);}
  appendChild(x){this.children.push(x);return x;}
  replaceChildren(...x){this.children=[...x];}
  addEventListener(n,fn){(this.listeners[n]??=[]).push(fn);}
  setAttribute(){}
  remove(){}
  click(){for(const fn of this.listeners.click||[])fn();}
  scrollIntoView(){}
  querySelector(){return null;}
}
function environment(slug, settings={}){
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'plugins',slug,'manifest.json'),'utf8'));
 const handlers=Object.create(null),header=new Element('header');
 const record={
  Title:{type:'SINGLE_LINE_TEXT',value:'  ＡＢＣ　'},Amount:{type:'NUMBER',value:'123'},
  Date:{type:'DATE',value:'2026-10-17'},Attachment:{type:'FILE',value:[]},
  Details:{type:'SUBTABLE',value:[{id:'1',value:{Qty:{type:'NUMBER',value:'3'}}}]},
  Email:{type:'SINGLE_LINE_TEXT',value:'user@example.com'},
  CustomerName:{type:'SINGLE_LINE_TEXT',value:''},Zip:{type:'SINGLE_LINE_TEXT',value:'1000001'},
  Address:{type:'SINGLE_LINE_TEXT',value:''},Barcode:{type:'SINGLE_LINE_TEXT',value:''}
 };
 const api={
  $PLUGIN_ID:'test-plugin',
  plugin:{app:{getConfig:()=>({ra_settings:JSON.stringify(settings)})}},
  events:{on:(names,fn)=>{for(const name of(Array.isArray(names)?names:[names])){assert.ok(name.startsWith('mobile.app.record.'),name);handlers[name]=fn;}}},
  mobile:{app:{
   getId:()=>48,
   getHeaderSpaceElement:()=>header,
   getFieldElements:()=>[],
   record:{
    get:()=>({record}),
    set:x=>{Object.assign(record,x.record);},
    getFieldElement:()=>null
   }
  }}
 };
 // No desktop kintone.app namespace: unsupported API access will fail.
 const c={
  console,JSON,URL,Blob,TextEncoder,Date,setTimeout,clearTimeout,
  navigator:{},
  location:{origin:'https://sandbox.cybozu.com',href:'https://sandbox.cybozu.com/k/m/48/show?record=1',assign:()=>{throw Error('unexpected navigation');}},
  document:{body:new Element('body'),head:new Element('head'),
   createElement:t=>new Element(t),
   getElementById:id=>header.children.find(x=>x.id===id)||null},
  kintone:api,requestAnimationFrame:()=>{},
  alert:()=>{},
  fetch:()=>{throw Error('unexpected fetch on page load');}
 };
 c.window=c;c.globalThis=c;
 vm.createContext(c);
 for(const file of manifest.mobile?.js||[]){
  const content=fs.readFileSync(path.join(root,'plugins',slug,file),'utf8');
  vm.runInContext(content,c,{timeout:1200,filename:slug+':'+file});
 }
 return {c,record,header,handlers,manifest};
}
test('16 mobile candidates provide only official mobile event names and dependencies',()=>{
 assert.equal(catalog.length,18);
 for(const item of catalog){
  const {slug}=item,m=JSON.parse(fs.readFileSync(path.join(root,'plugins',slug,'manifest.json'),'utf8'));
  if(supported.has(slug)){
   assert.ok(m.mobile?.js?.length>0,slug);
   for(const name of m.mobile.js)assert.ok(fs.existsSync(path.join(root,'plugins',slug,name)));
  }else assert.equal(m.mobile,undefined,slug+' should remain desktop-only');
 }
});
for(const slug of supported){
 test(slug+': register mobile hooks and handle simulated pages without desktop API',()=>{
  const a=environment(slug);
  const names=Object.keys(a.handlers);
  assert.ok(names.length>0,slug);
  const fixtures={record:a.record,records:[a.record],reuse:true,
   appId:48,viewType:'list'};
  for(const name of names){
   const evt={type:name,...fixtures};
   const out=a.handlers[name](evt);
   assert.equal(out,evt,'Expected original event return '+slug+' '+name);
  }
  if(slug==='input-template'){
   const p=a.header.children.find(x=>x.id==='ra-mini-input-template');
   assert.ok(p,'Mobile header menu should be used');
  }
  if(slug==='reuse-reset')assert.equal(a.record.Date.value,null);
  if(slug==='text-normalizer')assert.equal(a.record.Title.value,'ABC');
 });
}
test('input-template mobile actions call kintone.mobile.app.record.set',()=>{
 const {c,header,record,handlers}=environment('input-template');
 const evt={type:'mobile.app.record.create.show',record,appId:48};
 handlers['mobile.app.record.create.show'](evt);
 const p=header.children.find(x=>x.id==='ra-mini-input-template');
 const button=p?.children.find(x=>x.tagName==='BUTTON');
 assert.ok(button);
 button.click();
 assert.equal(record.Title.value,'サンプル');
});
test('mobile events cannot create a desktop-only redirect handler',()=>{
 const m=JSON.parse(fs.readFileSync(path.join(root,'plugins/save-navigation/manifest.json'),'utf8'));
 assert.equal(m.mobile,undefined);
});
test('mobile sticky-list is not enabled without redesigned mobile CSS',()=>{
 const m=JSON.parse(fs.readFileSync(path.join(root,'plugins/sticky-list/manifest.json'),'utf8'));
 assert.equal(m.mobile,undefined);
});
