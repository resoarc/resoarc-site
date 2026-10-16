import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker/src/index.mjs';

const f={id:'batch-main',name:'Batch Flow',cron:'0 18 * * *',steps:[
  {type:'read',app:12,query:'Status = "New"'},
  {type:'update',fields:{Status:'Done'}}
]};
const env=extra=>({
  KINTONE_DOMAIN:'example.cybozu.com',
  KINTONE_API_TOKENS:'SAMPLE123',
  WORKFLOWS_JSON:JSON.stringify({workflows:[f]}),
  RA_ALLOW_WRITES:'false',...extra
});

test('scheduled dry-run fetches data without updates',async()=>{
  const original=globalThis.fetch,calls=[];
  globalThis.fetch=async(url,init)=>{
    calls.push({url,init});
    return {ok:true,json:async()=>({records:[{$id:{value:'1'}}]})};
  };
  try{
    await worker.scheduled({cron:'0 18 * * *'},env(),{});
    assert.equal(calls.length,1);
    assert.match(calls[0].url,/k\/v1\/records\.json/);
    assert.equal(calls[0].init.method,'GET');
  }finally{globalThis.fetch=original;}
});
test('scheduled write mode performs an update',async()=>{
  const original=globalThis.fetch,calls=[];
  globalThis.fetch=async(url,init)=>{
    calls.push(init);
    return {ok:true,json:async()=>init.method==='GET'?{records:[{$id:{value:'5'}}]}:{}};
  };
  try{
    await worker.scheduled({cron:'0 18 * * *'},env({RA_ALLOW_WRITES:'true'}),{});
    assert.deepEqual(calls.map(c=>c.method),['GET','PUT']);
    assert.equal(JSON.parse(calls[1].body).app,12);
  }finally{globalThis.fetch=original;}
});
test('other cron must not read any records',async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('must not be called')};
  try{await worker.scheduled({cron:'0 0 * * *'},env(),{});}
  finally{globalThis.fetch=original;}
});
test('rejects non-kintone origins',async()=>{
  await assert.rejects(worker.scheduled({cron:'0 18 * * *'},env({KINTONE_DOMAIN:'evil.example.org'}),{}),/許可されたkintoneドメイン/);
});
test('public fetch endpoint cannot execute workflows',async()=>{
  const response=await worker.fetch(new Request('https://example.com/run'),env(),{});
  assert.equal(response.status,404);
});
