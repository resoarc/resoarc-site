import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker/src/index.mjs';

const field=value=>({value});
const job=()=>({
  $id:field('3'),$revision:field('1'),BatchName:field('Once'),
  BatchEnabled:field('有効'),RunState:field('待機'),
  ScheduleType:field('一回'),OneTimeAt:field('2026-10-15T00:00:00Z'),
  NextRunAt:field('2026-10-15T00:00:00Z'),RunHistory:field(''),
  Steps:field([{value:{TaskType:field('登録'),TargetApp:field('31'),
    Query:field(''),FieldsJSON:field('{"Description":"Created by Clock"}')}}])
});
const env=(patch={})=>({
  KINTONE_DOMAIN:'example.cybozu.com',KINTONE_API_TOKENS:'UNITTESTTOKEN',
  RA_CONTROL_APP_ID:'9',RA_CLOCK_ENABLED:'true',RA_ALLOW_WRITES:'true',RA_ALLOW_UNSCOPED_WRITES:'true',...patch
});

test('disabled Clock makes no outbound requests',async()=>{
  const old=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('disabled Clock contacted kintone')};
  try{
    await worker.scheduled({cron:'* * * * *'},env({RA_CLOCK_ENABLED:'false'}),{});
  }finally{globalThis.fetch=old;}
});
test('credential/authentication problems on claim are not mistaken for harmless concurrency',async()=>{
  const old=globalThis.fetch;
  let calls=0;
  globalThis.fetch=async(url,init)=>{
    calls++;
    if(init.method==='GET')return {ok:true,json:async()=>({records:[job()]})};
    return {ok:false,status:403,json:async()=>({})};
  };
  try{
    await assert.rejects(worker.scheduled({cron:'* * * * *'},env(),{}),/kintone API 403/);
    assert.equal(calls,2);
  }finally{globalThis.fetch=old;}
});
test('a one-time batch runs once across three consecutive cron ticks',async()=>{
  const old=globalThis.fetch;
  const current=job(),business=[];
  let requests=0;
  globalThis.fetch=async(url,init)=>{
    requests++;
    const u=new URL(url);
    const body=init.body?JSON.parse(init.body):{};
    const isControl=u.searchParams.get('app')==='9'||body.app===9;
    if(init.method==='GET'&&isControl){
      const enabled=current.BatchEnabled.value==='有効';
      const ready=current.RunState.value==='待機'||current.RunState.value==='正常終了';
      return {ok:true,json:async()=>({records:enabled&&ready?[structuredClone(current)]:[]})};
    }
    if(init.method==='PUT'&&isControl){
      if(body.revision!==current.$revision.value)return {ok:false,status:409};
      for(const [k,v] of Object.entries(body.record))current[k]=structuredClone(v);
      current.$revision.value=String(Number(current.$revision.value)+1);
      return {ok:true,json:async()=>({revision:current.$revision.value})};
    }
    if(init.method==='POST'&&body.app===31){
      business.push(body.records);
      return {ok:true,json:async()=>({ids:['40']})};
    }
    throw Error('Unexpected request: '+init.method+' '+u.pathname);
  };
  try{
    await worker.scheduled({cron:'* * * * *'},env(),{});
    assert.equal(business.length,1);
    assert.equal(current.RunState.value,'正常終了');
    assert.equal(current.BatchEnabled.value,'停止');
    assert.equal(current.RunHistory.value.split('\n').length,1);
    assert.ok(current.RunToken.value);
    const before=requests;
    await worker.scheduled({cron:'* * * * *'},env(),{});
    await worker.scheduled({cron:'* * * * *'},env(),{});
    assert.equal(business.length,1);
    assert.equal(requests-before,2); // control app lookup only on subsequent ticks
  }finally{globalThis.fetch=old;}
});
test('an ambiguous failure stops the job rather than retrying a duplicate create',async()=>{
  const old=globalThis.fetch, current=job();
  let businessCalls=0;
  globalThis.fetch=async(url,init)=>{
    const u=new URL(url);
    const body=init.body?JSON.parse(init.body):{};
    if(init.method==='GET'&&u.searchParams.get('app')==='9'){
      const due=current.RunState.value==='待機';
      return {ok:true,json:async()=>({records:due?[structuredClone(current)]:[]})};
    }
    if(init.method==='PUT'&&body.app===9){
      for(const [k,v] of Object.entries(body.record))current[k]=structuredClone(v);
      current.$revision.value=String(Number(current.$revision.value)+1);
      return {ok:true,json:async()=>({revision:current.$revision.value})};
    }
    if(init.method==='POST'&&body.app===31){
      businessCalls++;
      return {ok:false,status:503};
    }
    throw Error('Unexpected request');
  };
  try{
    await worker.scheduled({cron:'* * * * *'},env(),{});
    assert.equal(current.RunState.value,'要確認');
    assert.equal(businessCalls,1);
    await worker.scheduled({cron:'* * * * *'},env(),{});
    assert.equal(businessCalls,1);
  }finally{globalThis.fetch=old;}
});
