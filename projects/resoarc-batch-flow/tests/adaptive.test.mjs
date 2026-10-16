import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {runAdaptiveClock} from '../worker/src/adaptive-clock.mjs';
const require=createRequire(import.meta.url);
const core=require('../src/js/core.js');
const val=value=>({value});
const start=Date.parse('2026-10-17T00:00:00Z');
const when=m=>new Date(start+m*60_000);
function kv(){
  const data=new Map();const count={gets:0,puts:0};
  return {count,async get(key){count.gets++;return data.get(key)??null;},
    async put(key,value){count.puts++;data.set(key,value);},raw:data};
}
function job(time,kind='一回'){
  return {$id:val('5'),$revision:val('1'),
    BatchName:val('Adaptive polling test'),BatchEnabled:val('有効'),RunState:val('待機'),
    ScheduleType:val(kind),DailyTime:val('09:07'),
    OneTimeAt:val(new Date(time).toISOString()),IntervalMinutes:val('1'),
    NextRunAt:val(new Date(time).toISOString()),RunHistory:val(''),
    Steps:val([{value:{TaskType:val('read'),TargetApp:val('10'),Query:val(''),FieldsJSON:val('')}}])};
}
function fakeTenant(records){
  const calls={control:0,business:0,writes:0}, all=records;
  return {calls,async transport(path,method,params){
    if(path==='/k/v1/records.json'&&method==='GET'&&params.app===99){
      calls.control++;
      return {records:all.filter(r=>r.BatchEnabled.value==='有効' &&
        ['待機','正常終了'].includes(r.RunState.value) &&
        (!params.query.includes('NextRunAt != ""') || Boolean(r.NextRunAt?.value)))
        .sort((a,b)=>Date.parse(a.NextRunAt.value)-Date.parse(b.NextRunAt.value))
        .slice(0,3).map(r=>structuredClone(r))};
    }
    if(path==='/k/v1/records.json'&&method==='GET'&&params.app===10){
      calls.business++;return {records:[]};
    }
    if(path==='/k/v1/record.json'&&method==='PUT'&&params.app===99){
      calls.writes++;
      const rec=all.find(r=>r.$id.value===params.id);
      if(!rec||rec.$revision.value!==params.revision)
        throw Object.assign(Error('revision conflict'),{status:409});
      for(const [k,v] of Object.entries(params.record))rec[k]=structuredClone(v);
      rec.$revision.value=String(Number(rec.$revision.value)+1);
      return {revision:rec.$revision.value};
    }
    throw Error('unexpected '+method+' '+path);
  }};
}
const env=store=>({RA_CLOCK_STATE:store,RA_CONTROL_APP_ID:'99',RA_ALLOW_WRITES:'true'});
const quiet=async fn=>{
  const old=console.info;console.info=()=>{};
  try{return await fn();}finally{console.info=old;}
};
test('no jobs: 1440 minute cron ticks -> 144 kintone requests / 144 KV writes',async()=>{
  const store=kv(),tenant=fakeTenant([]);
  await quiet(async()=>{
    for(let minute=0;minute<1440;minute++){
      await runAdaptiveClock(env(store),tenant.transport,core,when(minute));
    }
  });
  assert.equal(tenant.calls.control,144);
  assert.equal(store.count.gets,1440);
  assert.equal(store.count.puts,144);
});
test('a future one-time job is run on the scheduled minute, then disabled',async()=>{
  const store=kv(),record=job(when(7)),tenant=fakeTenant([record]);
  await quiet(async()=>{
    for(let minute=0;minute<=12;minute++){
      await runAdaptiveClock(env(store),tenant.transport,core,when(minute));
    }
  });
  assert.equal(tenant.calls.business,1);
  assert.equal(tenant.calls.writes,2);
  assert.equal(record.RunState.value,'正常終了');
  assert.equal(record.BatchEnabled.value,'停止');
  assert.equal(tenant.calls.control,3); // 00:00, 00:07, 00:10
});
test('when schedule moved earlier, 10-minute resync detects it',async()=>{
  const store=kv(),record=job(when(45)),tenant=fakeTenant([record]);
  await quiet(async()=>{
    await runAdaptiveClock(env(store),tenant.transport,core,when(0));
    record.NextRunAt=val(when(3).toISOString());
    record.OneTimeAt=val(when(3).toISOString());
    for(let minute=1;minute<=9;minute++){
      const result=await runAdaptiveClock(env(store),tenant.transport,core,when(minute));
      assert.equal(result.polled,false);
    }
    await runAdaptiveClock(env(store),tenant.transport,core,when(10));
  });
  assert.equal(tenant.calls.business,1);
  assert.equal(tenant.calls.control,2);
});
test('ongoing every-minute dry run throttles KV writes to at most once in two minutes',async()=>{
  const store=kv(),record=job(when(0),'間隔'),tenant=fakeTenant([record]);
  await quiet(async()=>{
    for(let minute=0;minute<120;minute++)
      await runAdaptiveClock({...env(store),RA_ALLOW_WRITES:'false'},tenant.transport,core,when(minute));
  });
  assert.equal(tenant.calls.control,120);
  assert.ok(store.count.puts<=60);
});
test('missing or broken KV fails closed instead of polling kintone',async()=>{
  const tenant=fakeTenant([]);
  await assert.rejects(runAdaptiveClock({RA_CONTROL_APP_ID:'99'},tenant.transport,core,when(0)),/KV/);
  const store=kv();store.get=async()=>{throw Error('KV temporarily unavailable')};
  await assert.rejects(runAdaptiveClock(env(store),tenant.transport,core,when(0)),/unavailable/);
  assert.equal(tenant.calls.control,0);
});
test('corrupt KV state triggers a controlled resynchronization',async()=>{
  const store=kv(),tenant=fakeTenant([]);
  store.raw.set('resoarc-clock:v1:app:99','{broken json}');
  const result=await quiet(()=>runAdaptiveClock(env(store),tenant.transport,core,when(0)));
  assert.equal(result.polled,true);
  assert.equal(tenant.calls.control,1);
  assert.equal(store.count.puts,1);
});

test('three due jobs are drained over two minutes without losing the third',async()=>{
  const store=kv();
  const records=Array.from({length:3},(_,i)=>{
    const r=job(when(0));
    r.$id=val(String(20+i));
    return r;
  });
  const tenant=fakeTenant(records);
  await quiet(async()=>{
    const first=await runAdaptiveClock(env(store),tenant.transport,core,when(0));
    const second=await runAdaptiveClock(env(store),tenant.transport,core,when(1));
    assert.equal(first.outcomes.length,2);
    assert.equal(second.outcomes.length,1);
  });
  assert.equal(tenant.calls.business,3);
  assert.equal(tenant.calls.control,2);
  assert.ok(records.every(r=>r.BatchEnabled.value==='停止'));
});

test('draft records with missing NextRunAt cannot starve a due batch',async()=>{
  const store=kv(),due=job(when(0));
  due.$id=val('903');
  const blanks=Array.from({length:5},(_,i)=>{
    const r=job(when(20));r.$id=val(String(800+i));r.NextRunAt=val('');return r;
  });
  const tenant=fakeTenant([...blanks,due]);
  await quiet(async()=>{
    const outcome=await runAdaptiveClock(env(store),tenant.transport,core,when(0));
    assert.equal(outcome.due,1);
    assert.equal(outcome.outcomes[0].id,'903');
  });
  assert.equal(tenant.calls.business,1);
  assert.equal(due.BatchEnabled.value,'停止');
});
