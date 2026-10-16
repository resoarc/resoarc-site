const test=require('node:test');const assert=require('node:assert/strict');
const {normalize,plan}=require('../src/js/core.js');
const tabs=[{label:'基本',fields:['name','age']},{label:'契約',fields:['contract','memo']}];
test('normalizes valid groups',()=>assert.deepEqual(normalize(JSON.stringify(tabs)),tabs));
test('invalid groups rejected',()=>{
 for(const t of [[],[{label:'',fields:['name']}],[{label:'T',fields:[]}],[{label:'T',fields:['x','x']}],new Array(13).fill({label:'T',fields:['x']})])
  assert.equal(normalize(t),null);
});
test('rejects fields assigned to multiple tabs',()=>assert.equal(normalize([{label:'1',fields:['x']},{label:'2',fields:['x']}]),null));
test('hides only configured fields',()=>{
 const p=plan(tabs,1);
 assert.deepEqual(p,[{field:'name',shown:false},{field:'age',shown:false},{field:'contract',shown:true},{field:'memo',shown:true}]);
});
test('does not mutate provided config',()=>{
 const c=JSON.stringify(tabs);
 plan(tabs,0);
 assert.equal(JSON.stringify(tabs),c);
});
test('bounds',()=>{
 assert.equal(normalize([{label:'a'.repeat(31),fields:['x']}]),null);
 assert.equal(normalize([{label:'1',fields:new Array(101).fill(0).map((_,i)=>'field'+i)}]),null);
 assert.throws(()=>plan(tabs,10));
});
