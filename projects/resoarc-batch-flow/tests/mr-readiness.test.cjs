'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {schemaFields,evaluateSchema,matchingApps,inspectCenter}=require('../scripts/mr-batch-center-readiness.cjs');
const sampleSchema={properties:{
  BatchName:{type:'SINGLE_LINE_TEXT'},RunState:{type:'DROP_DOWN'},
  Steps:{type:'SUBTABLE',fields:{TaskType:{type:'DROP_DOWN'},TargetApp:{type:'NUMBER'}}}
}};
test('extract required top-level and subtable codes',()=>{
  assert.deepEqual(schemaFields(sampleSchema),{
    top:['BatchName','RunState','Steps'],table:['TaskType','TargetApp']
  });
});
test('report missing field and missing subtable column',()=>{
  const result=evaluateSchema({BatchName:{},Steps:{fields:{TaskType:{}}}},schemaFields(sampleSchema));
  assert.equal(result.ok,false);
  assert.deepEqual(result.missingFields,['RunState']);
  assert.deepEqual(result.missingTableFields,['TargetApp']);
});
test('complete control app field schema passes',()=>{
  const result=evaluateSchema({BatchName:{},RunState:{},Steps:{fields:{TaskType:{},TargetApp:{}}}},schemaFields(sampleSchema));
  assert.equal(result.ok,true);
});
test('only discover Batch Center apps, not auto-number app 48',()=>{
  const result=matchingApps([
    {name:'ResoArc 自動採番検証（専用テスト）',appId:'48'},
    {name:'ResoArc バッチ管理',appId:'70'},
    {name:'Other customer app',appId:'12'}
  ]);
  assert.deepEqual(result,[{name:'ResoArc バッチ管理',appId:70}]);
});
test('missing batch-center app is reported, without changes',async()=>{
  const calls=[];
  const browser={
    port:async()=>9222,
    loginUrl:'https://example.cybozu.com/k/48/',
    open:async()=>({id:'test'}),
    connect:async()=>({
      evalJS:async script=>{
        calls.push(script);
        if(script.includes('document.readyState'))return {loaded:true,loggedIn:true};
        return {ok:true,apps:[{name:'ResoArc 自動採番検証',appId:'48'}]};
      },
      close:()=>{}
    }),
    closeTab:async()=>{}
  };
  const result=await inspectCenter(browser,{},null);
  assert.equal(result.status,'not_provisioned');
  assert.equal(result.candidates.length,0);
  assert.equal(calls.length,2);
});
test('without dedicated browser, no connection is attempted',async()=>{
  const browser={port:async()=>null,open:()=>{throw Error('should not open')}};
  const result=await inspectCenter(browser,{},null);
  assert.equal(result.status,'isolated_browser_unavailable');
});
