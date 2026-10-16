import test from 'node:test';
import assert from 'node:assert/strict';
import {e2eScope,requireScopedFlow,runFromCenter} from '../worker/src/center-runner.mjs';
import {runAdaptiveClock} from '../worker/src/adaptive-clock.mjs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const core=require('../src/js/core.js');
const guarded={RA_CONTROL_APP_ID:'50',RA_ALLOW_WRITES:'true',RA_E2E_ONLY_BATCH_ID:'7',RA_E2E_ALLOWED_APP_ID:'52'};
test('E2E scope requires both valid decimal identifiers',()=>{
 assert.equal(e2eScope({}),null);
 assert.throws(()=>e2eScope({RA_E2E_ONLY_BATCH_ID:'7'}),/対象バッチID/);
 assert.throws(()=>e2eScope({RA_E2E_ALLOWED_APP_ID:'52'}),/対象バッチID/);
 assert.throws(()=>e2eScope({RA_E2E_ONLY_BATCH_ID:'0',RA_E2E_ALLOWED_APP_ID:'52'}),/対象バッチID/);
 assert.deepEqual(e2eScope(guarded),{id:'7',app:52});
});
test('E2E isolation permits only the specified batch, and only app52 operations',()=>{
 const s=e2eScope(guarded);
 const allowed={steps:[
  {type:'create',app:52,fields:{TestKey:'smoke'}},
  {type:'read',app:52,query:'TestKey = "smoke"'},
  {type:'update',fields:{Stage:'done'}},
  {type:'copy',app:52,fields:{Payload:'Stage'}}
 ]};
 assert.doesNotThrow(()=>requireScopedFlow(allowed,s,'7'));
 assert.throws(()=>requireScopedFlow(allowed,s,'8'),/対象以外/);
 assert.throws(()=>requireScopedFlow({steps:[{type:'read',app:48}]},s,'7'),/範囲外/);
 assert.throws(()=>requireScopedFlow({steps:[{type:'create',app:50}]},s,'7'),/範囲外/);
 assert.throws(()=>requireScopedFlow({steps:[{type:'update',fields:{Stage:'X'}}]},s,'7'),/範囲外/);
});
test('scoped minute dispatcher includes kintone record ID in query',async()=>{
 let queried=false;
 const out=await runFromCenter(guarded,async(_path,method,args)=>{
   assert.equal(method,'GET');assert.equal(args.app,50);
   assert.match(args.query,/\$id = "7"/);queried=true;
   return {records:[]};
 },core,'2026-10-17T00:00:00Z');
 assert.deepEqual(out,[]);assert.equal(queried,true);
});
test('scoped adaptive dispatcher never reads an unrelated active job',async()=>{
 const store=new Map();let reads=0;
 const env={...guarded,RA_CLOCK_STATE:{
  async get(k){return store.get(k)||null},
  async put(k,v){store.set(k,v)}
 }};
 const result=await runAdaptiveClock(env,async(_path,method,args)=>{
  reads++;
  assert.equal(method,'GET');
  assert.match(args.query,/\$id = "7"/);
  return {records:[]};
 },core,'2026-10-17T00:00:00Z');
 assert.equal(result.polled,true);assert.equal(reads,1);
});
