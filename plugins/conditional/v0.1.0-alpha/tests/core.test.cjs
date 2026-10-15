const test=require('node:test'),assert=require('node:assert/strict');
const c=require('../src/js/core.js');
const rules=[{source:'status',target:'reason',operator:'eq',value:'NG',required:true}];
test('valid rule schema',()=>assert.deepEqual(c.normalize(JSON.stringify(rules)),rules));
test('reject duplicate target and source=target',()=>{
 assert.equal(c.normalize([...rules,...rules]),null);
 assert.equal(c.normalize([{source:'x',target:'x',operator:'eq'}]),null);
});
test('operator comparisons',()=>{
 for(const [op,x,y,expected] of [
 ['eq','abc','abc',true],['neq','abc','xyz',true],
 ['includes','prefix-value','value',true],['gt','10','9',true],
 ['lt','1','2',true],['gte','3','3',true],['lte','3','3',true],
 ['gt','ABC','9',false],['eq',null,'',false],
 ['empty',' ', '',true],['not_empty','x','',true]]){
 assert.equal(c.match({operator:op,value:y},x),expected);
 }
});
test('supports arrays and empty values',()=>{
 assert.equal(c.empty([]),true);assert.equal(c.empty(0),false);
 assert.equal(c.match({operator:'includes',value:'red'},['red','blue']),true);
 assert.equal(c.match({operator:'eq',value:'red'},['blue']),false);
});
test('required only when condition true',()=>{
 const on=c.evaluate(rules,{status:{value:'NG'},reason:{value:''}});
 assert.equal(on[0].shown,true);assert.equal(on[0].required,true);
 const off=c.evaluate(rules,{status:{value:'OK'},reason:{value:'old'}});
 assert.equal(off[0].shown,false);assert.equal(off[0].required,false);
});
test('missing driver never hides target',()=>{
 const result=c.evaluate(rules,{reason:{value:'x'}});
 assert.equal(result[0].missing,true);assert.equal(result[0].shown,true);
});
