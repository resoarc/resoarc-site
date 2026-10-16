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
