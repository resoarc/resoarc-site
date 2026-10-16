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

test('real kintone GAIA_CO02 error skips the stale claim even if HTTP status is 400',async()=>{
  const field=v=>({value:v});
  const due={
    $id:field('7'),$revision:field('1'),BatchName:field('race smoke'),
    BatchEnabled:field('有効'),RunState:field('待機'),
    ScheduleType:field('一回'),OneTimeAt:field('2026-10-15T00:00:00Z'),
    NextRunAt:field('2026-10-15T00:00:00Z'),
    Steps:field([{value:{
      TaskType:field('登録'),TargetApp:field('52'),Query:field(''),
      FieldsJSON:field('{"TestKey":"should-not-write"}')
    }}])
  };
  let claimed=0, business=0;
  const transport=async(_path,method,body)=>{
    if(method==='GET' && body.app===50)return {records:[due]};
    if(method==='PUT' && body.app===50){
      claimed++;
      const e=Object.assign(Error('GAIA_CO02'),{status:400,kintoneCode:'GAIA_CO02'});
      throw e;
    }
    business++;throw Error('Unexpected business write!');
  };
  const outcomes=await runFromCenter(guarded,transport,core,'2026-10-17T00:00:00Z');
  assert.equal(outcomes.length,1);
  assert.equal(outcomes[0].skipped,true);
  assert.equal(claimed,1);
  assert.equal(business,0);
});
test('kintone REST adapter safely preserves conflict error code without surfacing body',async()=>{
  const {adapter}=await import('../worker/src/index.mjs');
  const original=globalThis.fetch;
  globalThis.fetch=async()=>({ok:false,status:400,json:async()=>({code:'GAIA_CO02',message:'Do not expose details'})});
  try{
    const transport=adapter({KINTONE_DOMAIN:'example.cybozu.com',KINTONE_API_TOKENS:'TESTTOKEN'});
    await assert.rejects(transport('/k/v1/record.json','PUT',{app:50,id:7,revision:'1',record:{}}),
      err=>err.status===400 && err.kintoneCode==='GAIA_CO02' && !err.message.includes('Do not expose'));
  }finally{globalThis.fetch=original;}
});

test('legacy JSON engine cannot bypass an E2E test scope without a control-app binding',async()=>{
 const worker=(await import('../worker/src/index.mjs')).default;
 const original=globalThis.fetch;
 globalThis.fetch=()=>{throw Error('No network allowed')};
 try{
   await assert.rejects(worker.scheduled({cron:'0 18 * * *'},{
     RA_CLOCK_ENABLED:'true',
     RA_E2E_ONLY_BATCH_ID:'7',
     RA_E2E_ALLOWED_APP_ID:'52',
     WORKFLOWS_JSON:JSON.stringify({workflows:[{id:'test',name:'test',cron:'0 18 * * *',steps:[{type:'create',app:48,fields:{}}]}]})
   },{}),/管理アプリIDが必須/);
 }finally{globalThis.fetch=original;}
});
