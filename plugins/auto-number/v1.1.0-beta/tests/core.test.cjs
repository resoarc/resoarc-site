const test = require('node:test');const assert=require('node:assert/strict');const {validConfig,makeNumber}=require('../src/js/core.js');
const cfg={field:'number',prefix:'INV-',width:'6',start:'1'};
test('normal numbering',()=>{assert.equal(makeNumber('1',cfg),'INV-000001');assert.equal(makeNumber('12',cfg),'INV-000012');assert.equal(makeNumber('1000000',cfg),'INV-1000000');});
test('offset numbering',()=>assert.equal(makeNumber('1',{...cfg,start:'100'}),'INV-000100'));
test('large ID without precision loss',()=>assert.equal(makeNumber('9007199254740993',{...cfg,prefix:''}),'9007199254740993'));
test('deterministic concurrent records',()=>{const seen=new Set();for(let i=1;i<=10000;i++){const n=makeNumber(String(i),cfg);assert.ok(!seen.has(n));seen.add(n);}});
test('invalid inputs',()=>{for(const id of ['',0,-1,'1.2','01','abc'])assert.throws(()=>makeNumber(id,cfg));for(const c of [{...cfg,width:'2'},{...cfg,prefix:'日本語'},{...cfg,prefix:'/'.repeat(21)},{...cfg,start:'0'},{...cfg,field:''}])assert.equal(validConfig(c),null);});
test('no truncation after width exceeded',()=>assert.equal(makeNumber('123456',{...cfg,width:'3'}),'INV-123456'));
