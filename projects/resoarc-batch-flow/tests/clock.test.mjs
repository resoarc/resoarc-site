import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import worker from '../worker/src/index.mjs';

const folder=dirname(fileURLToPath(import.meta.url));
const settings=JSON.parse(readFileSync(resolve(folder,'../worker/center-wrangler.example.jsonc'),'utf8'));
const val=value=>({value});
const due=()=>({
  $id:val('23'),$revision:val('7'),
  BatchName:val('Clock test'),
  BatchEnabled:val('有効'),RunState:val('待機'),
  DailyTime:val('12:00'),NextRunAt:val('2020-01-01T03:00:00Z'),RunHistory:val(''),
  Steps:val([{value:{TaskType:val('登録'),TargetApp:val('8'),Query:val(''),FieldsJSON:val('{"Memo":"clock-test"}')}}])
});
function env(allow='false'){
  return {KINTONE_DOMAIN:'example.cybozu.com',KINTONE_API_TOKENS:'SAMPLE123',RA_CONTROL_APP_ID:'99',RA_CLOCK_ENABLED:'true',RA_ALLOW_WRITES:allow,RA_ALLOW_UNSCOPED_WRITES:'true'};
}
test('scheduled write mode refuses unscoped writes unless independently enabled',async()=>{
  const before=globalThis.fetch;let requests=0;
  globalThis.fetch=async()=>{requests++;throw Error('No request expected');};
  try{
    const config=env('true');
    delete config.RA_ALLOW_UNSCOPED_WRITES;
    await assert.rejects(worker.scheduled({cron:'* * * * *'},config,{}),/Unscoped write execution/);
    assert.equal(requests,0);
  }finally{globalThis.fetch=before;}
});
test('clock configuration uses exactly one minute trigger',()=>{
  assert.deepEqual(settings.triggers.crons,['* * * * *']);
  assert.equal(settings.vars.RA_ALLOW_WRITES,'false');
  assert.equal(settings.vars.RA_CLOCK_ENABLED,'false');
  assert.equal(settings.vars.RA_CONTROL_APP_ID,'0');
  assert.equal(settings.workers_dev,false);
  assert.equal(settings.preview_urls,false);
});
test('scheduled entry queries the control app only when there are no jobs',async()=>{
  const old=globalThis.fetch, calls=[];
  globalThis.fetch=async(url,init)=>{
    calls.push({url,init});
    return {ok:true,json:async()=>({records:[]})};
  };
  try{
    await worker.scheduled({cron:'* * * * *'},env('true'),{});
    assert.equal(calls.length,1);
    const u=new URL(calls[0].url);
    assert.equal(u.searchParams.get('app'),'99');
    assert.match(u.searchParams.get('query'),/NextRunAt <=/);
    assert.equal(calls[0].init.method,'GET');
  }finally{globalThis.fetch=old;}
});
test('scheduled entry dispatches one due batch, writes and finalizes with token',async()=>{
  const old=globalThis.fetch, calls=[];
  globalThis.fetch=async(url,init)=>{
    const u=new URL(url), body=init.body?JSON.parse(init.body):null;
    calls.push({url,method:init.method,body,headers:init.headers});
    if(init.method==='GET'&&u.searchParams.get('app')==='99'){
      return {ok:true,json:async()=>({records:[due()]})};
    }
    if(init.method==='POST'){
      return {ok:true,json:async()=>({ids:['11'],revisions:['1']})};
    }
    if(init.method==='PUT'){
      return {ok:true,json:async()=>({revision:'8'})};
    }
    throw Error('unexpected API');
  };
  try{
    await worker.scheduled({cron:'* * * * *'},env('true'),{});
    assert.deepEqual(calls.map(c=>c.method),['GET','PUT','POST','PUT']);
    assert.equal(calls[0].headers['X-Cybozu-API-Token'],'SAMPLE123');
    assert.equal(calls[1].body.revision,'7');
    assert.equal(calls[1].body.record.RunState.value,'実行中');
    assert.equal(calls[2].body.app,8);
    assert.equal(calls[3].body.record.RunState.value,'正常終了');
  }finally{globalThis.fetch=old;}
});
