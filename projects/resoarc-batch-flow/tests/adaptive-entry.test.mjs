import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker/src/index.mjs';
const config=()=>({KINTONE_DOMAIN:'example.cybozu.com',KINTONE_API_TOKENS:'UNITTESTTOKEN',
  RA_CONTROL_APP_ID:'99',RA_CLOCK_ENABLED:'true',RA_ALLOW_WRITES:'false',RA_POLL_MODE:'adaptive'});
test('scheduled adaptive mode fails closed without KV before any kintone request',async()=>{
  const old=globalThis.fetch;let calls=0;
  globalThis.fetch=async()=>{calls++;return {ok:true,json:async()=>({records:[]})};};
  try{
    await assert.rejects(worker.scheduled({cron:'* * * * *'},config(),{}),/RA_CLOCK_STATE/);
    assert.equal(calls,0);
  }finally{globalThis.fetch=old;}
});
test('two successive scheduled() calls reuse KV and avoid second kintone API call',async()=>{
  const old=globalThis.fetch, store=new Map();let requests=0;
  globalThis.fetch=async()=>{requests++;return {ok:true,json:async()=>({records:[]})};};
  const state={
    async get(k){return store.get(k)||null;},
    async put(k,v){store.set(k,v);}
  };
  try{
    const env={...config(),RA_CLOCK_STATE:state};
    const first=await worker.scheduled({cron:'* * * * *'},env,{});
    const second=await worker.scheduled({cron:'* * * * *'},env,{});
    assert.equal(first.polled,true);
    assert.equal(second.polled,false);
    assert.equal(requests,1);
  }finally{globalThis.fetch=old;}
});
