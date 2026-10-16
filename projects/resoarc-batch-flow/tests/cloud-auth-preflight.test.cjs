'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {safeConfig,checkAuth}=require('../scripts/cloud-auth-preflight.cjs');
function valid(){
 return {name:'resoarc-clock-self-hosted',workers_dev:false,preview_urls:false,
 triggers:{crons:['* * * * *']},
 kv_namespaces:[{binding:'RA_CLOCK_STATE',id:'TEST-ONLY'}],
 vars:{RA_CLOCK_ENABLED:'true',RA_ALLOW_WRITES:'false',RA_POLL_MODE:'adaptive',RA_CONTROL_APP_ID:'50'}};
}
test('preflight accepts only one disabled-write adaptive Clock with private URL',()=>assert.equal(safeConfig(valid()),true));
test('rejects enabled writes even with otherwise valid settings',()=>{const c=valid();c.vars.RA_ALLOW_WRITES='true';assert.equal(safeConfig(c),false)});
test('rejects missing KV and public HTTP endpoint',()=>{
 const c=valid();delete c.kv_namespaces;assert.equal(safeConfig(c),false);
 const a=valid();a.workers_dev=true;assert.equal(safeConfig(a),false);
});
test('rejects disabled and non-test app configurations',()=>{
 const c=valid();c.vars.RA_CONTROL_APP_ID='0';assert.equal(safeConfig(c),false);
 const a=valid();a.vars.RA_CLOCK_ENABLED='false';assert.equal(safeConfig(a),false);
});
test('whoami succeeds only for a successful CLI status and hides account output',()=>{
 assert.equal(checkAuth(()=>({status:0,stdout:'account email private',stderr:''})),true);
 assert.equal(checkAuth(()=>({status:1,stderr:'token expired'})),false);
 assert.equal(checkAuth(()=>({status:null,error:new Error('timeout')})),false);
});

test('Cloudflare target access must be verified separately from whoami',()=>{
 const {checkWorkerAccess}=require('../scripts/cloud-auth-preflight.cjs');
 assert.equal(checkWorkerAccess(()=>({status:0,stdout:'[]',stderr:''})),true);
 assert.equal(checkWorkerAccess(()=>({status:1,stdout:'',stderr:'interactive login required'})),false);
 assert.equal(checkWorkerAccess(()=>({status:0,stdout:'not-json',stderr:''})),false);
});

test('chooseDeployedVersion rejects missing, split, and malformed deployments',()=>{
 const {chooseDeployedVersion}=require('../scripts/cloud-auth-preflight.cjs');
 const id='d611cd99-6433-490f-be2d-3fcf73a762c0';
 assert.equal(chooseDeployedVersion([]),null);
 assert.equal(chooseDeployedVersion([{created_on:'2026-10-17T00:00:00Z',versions:[{version_id:id,percentage:50}]}]),null);
 assert.equal(chooseDeployedVersion([{created_on:'2026-10-17T00:00:00Z',versions:[{version_id:'not a uuid',percentage:100}]}]),null);
 assert.equal(chooseDeployedVersion([{created_on:'2026-10-16T00:00:00Z',versions:[{version_id:'dddddddd-0000-0000-0000-000000000000',percentage:100}]},{created_on:'2026-10-17T00:00:00Z',versions:[{version_id:id,percentage:100}]}]),id);
});
test('actual deployed bindings must be read-only and match the expected test app',()=>{
 const {verifyRemoteBindings}=require('../scripts/cloud-auth-preflight.cjs');
 const b=[
  {name:'RA_CONTROL_APP_ID',type:'plain_text',text:'50'},
  {name:'RA_CLOCK_ENABLED',type:'plain_text',text:'true'},
  {name:'RA_POLL_MODE',type:'plain_text',text:'adaptive'},
  {name:'RA_ALLOW_WRITES',type:'plain_text',text:'false'},
  {name:'RA_CLOCK_STATE',type:'kv_namespace'},
  {name:'KINTONE_DOMAIN',type:'secret_text'},
  {name:'KINTONE_API_TOKENS',type:'secret_text'}
 ];
 assert.equal(verifyRemoteBindings({resources:{bindings:b}},valid()),true);
 assert.equal(verifyRemoteBindings({resources:{bindings:b.map(x=>x.name==='RA_ALLOW_WRITES'?{...x,text:'true'}:x)}},valid()),false);
 assert.equal(verifyRemoteBindings({resources:{bindings:b.filter(x=>x.name!=='RA_CLOCK_STATE')}},valid()),false);
 assert.equal(verifyRemoteBindings({resources:{bindings:b.map(x=>x.name==='RA_CONTROL_APP_ID'?{...x,text:'48'}:x)}},valid()),false);
 assert.equal(verifyRemoteBindings({resources:{bindings:[...b,b[0]]}},valid()),false);
});
test('deployment read requires valid version detail, no mere login/empty list acceptance',()=>{
 const {checkDeployedSafety}=require('../scripts/cloud-auth-preflight.cjs');
 assert.deepEqual(checkDeployedSafety(valid(),()=>({status:0,stdout:'[]'})),{targetAccessible:true,remoteReadOnlyVerified:false});
 assert.deepEqual(checkDeployedSafety(valid(),()=>({status:1,stderr:'auth expired'})),{targetAccessible:false,remoteReadOnlyVerified:false});
});
