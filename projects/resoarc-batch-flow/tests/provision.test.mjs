import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import vm from 'node:vm';
import {buildClockLayout,provisionClockApp} from '../control-app/provision-core.mjs';

const dir=dirname(fileURLToPath(import.meta.url));
const schema=createRequire(import.meta.url)('../control-app/fields.json').properties;
const installer=readFileSync(resolve(dir,'../release/resoarc-clock-bootstrap-v0.3.2.js'),'utf8');
function fakeAppSession(confirmResult){
  const requests=[];
  const messages=[];
  const resultMap={
    '/k/v1/preview/app.json':{app:'813',revision:'1'},
    '/k/v1/preview/app/form/fields.json':{revision:'2'},
    '/k/v1/preview/app/form/layout.json':{revision:'3'},
    '/k/v1/preview/app/deploy.json':{}
  };
  const context={
    location:{hostname:'resoarc-test.cybozu.com'},
    confirm:()=>confirmResult,
    console:{info:(...xs)=>messages.push(xs),error:(...xs)=>messages.push(xs)},
    kintone:{api:Object.assign(async(path,method,params)=>{
      requests.push({path,method,params});
      if(!Object.hasOwn(resultMap,path))throw Error('Unexpected URL');
      return resultMap[path];
    },{url:p=>p})}
  };
  return {context,requests,messages};
}
test('form includes every custom field exactly once, and no duplicate table columns',()=>{
  const layout=buildClockLayout(schema);
  const codes=layout.flatMap(row=>row.type==='SUBTABLE'
    ? [row.code,...row.fields.map(f=>f.code)]
    : row.fields.map(f=>f.code));
  const expected=Object.keys(schema).flatMap(k=>schema[k].type==='SUBTABLE'
    ? [k,...Object.keys(schema[k].fields)] : [k]);
  assert.equal(new Set(codes).size,codes.length);
  assert.deepEqual([...codes].sort(),[...expected].sort());
});
test('installer refuses creation if user cancels confirmation',async()=>{
  const {context,requests}=fakeAppSession(false);
  const result=await vm.runInNewContext(installer,context);
  assert.equal(result.cancelled,true);
  assert.equal(requests.length,0);
});
test('installer on a logged-in test tenant creates only a new app then deploys it',async()=>{
  const {context,requests}=fakeAppSession(true);
  const result=await vm.runInNewContext(installer,context);
  assert.equal(result.app,813);
  assert.deepEqual(requests.map(c=>[c.path,c.method]),[
    ['/k/v1/preview/app.json','POST'],
    ['/k/v1/preview/app/form/fields.json','POST'],
    ['/k/v1/preview/app/form/layout.json','PUT'],
    ['/k/v1/preview/app/deploy.json','POST']
  ]);
  assert.equal(requests[0].params.name,'ResoArc Clock 検証用');
  assert.equal(requests[1].params.app,813);
  assert.equal(requests[1].params.properties.BatchEnabled.defaultValue,'停止');
  assert.equal(requests[2].params.layout.at(-1).type,'SUBTABLE');
  assert.equal(requests[3].params.apps[0].revision,'3');
  assert.equal(result.status,'deploy_requested');
});
test('installer rejects other domains, without touching network',async()=>{
  const {context,requests}=fakeAppSession(true);
  context.location.hostname='malicious.example.com';
  await assert.rejects(vm.runInNewContext(installer,context),/your own kintone/);
  assert.equal(requests.length,0);
});
test('failed app provisioning exposes the newly created preview app ID',async()=>{
  let count=0;
  await assert.rejects(async()=>provisionClockApp(async()=>{
    count++;
    if(count===1)return {app:'919'};
    throw Error('field schema rejected');
  },schema),e=>e.message==='field schema rejected'&&e.clockAppId===919);
  assert.equal(count,2);
});
