import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {adapter} from '../worker/src/index.mjs';

const settings={
  KINTONE_DOMAIN:'example.cybozu.com',
  KINTONE_API_TOKENS:'TESTTOKEN123',
  RA_CONTROL_APP_ID:'23',
  RA_ALLOW_WRITES:'true'
};

test('Clock requires explicit opt-in even with app id and valid credentials', async()=>{
  const before=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('disabled Clock must not call network')};
  try{
    await worker.scheduled({cron:'* * * * *'},settings,{});
    await worker.scheduled({cron:'* * * * *'},{...settings,RA_CLOCK_ENABLED:'yes'},{});
    await worker.scheduled({cron:'* * * * *'},{...settings,RA_CLOCK_ENABLED:'false'},{});
  }finally{globalThis.fetch=before;}
});

test('legacy scheduled workflows require explicit opt-in as well', async()=>{
  const before=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('missing flag must disable all network activity')};
  try{await worker.scheduled({cron:'0 18 * * *'},{KINTONE_DOMAIN:'example.cybozu.com',KINTONE_API_TOKENS:'TESTTOKEN123'},{});}
  finally{globalThis.fetch=before;}
});

test('single-record GET uses id and never query=undefined',async()=>{
  const before=globalThis.fetch,requests=[];
  globalThis.fetch=async (url,init)=>{
    requests.push({url:new URL(url),init});
    return {ok:true,json:async()=>({record:{$id:{value:'42'}}})};
  };
  try{
    const result=await adapter(settings)('/k/v1/record.json','GET',{app:23,id:42});
    assert.equal(result.record.$id.value,'42');
    assert.equal(requests.length,1);
    assert.equal(requests[0].url.searchParams.get('id'),'42');
    assert.equal(requests[0].url.searchParams.get('app'),'23');
    assert.equal(requests[0].url.searchParams.has('query'),false);
    assert.equal(requests[0].init.method,'GET');
  }finally{globalThis.fetch=before;}
});

test('GET record without id fails before network',async()=>{
  const before=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('GET without id should never call network')};
  try{
    await assert.rejects(adapter(settings)('/k/v1/record.json','GET',{app:23}),/レコードIDが必要/);
  }finally{globalThis.fetch=before;}
});

test('API allowlist refuses unsupported operations without network',async()=>{
  const before=globalThis.fetch;
  globalThis.fetch=()=>{throw Error('unsupported operations should never call network')};
  try{
    const call=adapter(settings);
    await assert.rejects(call('/k/v1/record.json','POST',{app:23,record:{}}),/未対応/);
    await assert.rejects(call('/k/v1/app.json','GET',{app:23}),/未対応/);
    await assert.rejects(call('/k/v1/records.json','DELETE',{app:23}),/未対応/);
  }finally{globalThis.fetch=before;}
});

test('revision errors preserve HTTP status and do not become retries',async()=>{
  const before=globalThis.fetch;
  globalThis.fetch=async()=>({ok:false,status:409,json:async()=>({code:'GAIA_CO02'})});
  try{
    await assert.rejects(adapter(settings)('/k/v1/record.json','PUT',{app:23,id:42,revision:2,record:{}}),err=>{
      assert.equal(err.status,409);
      return true;
    });
  }finally{globalThis.fetch=before;}
});
