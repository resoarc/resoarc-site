import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {checkedOrigin,QA_ORIGIN} from '../scripts/qa-session.mjs';

const executable=fileURLToPath(new URL('../scripts/qa-api.mjs',import.meta.url));
function command(...args){
  return spawnSync(process.execPath,[executable,...args],{
    encoding:'utf8',timeout:6000,
    env:{...process.env,RESOARC_QA_STATE:'./uncreated-safe-qa-state.json'}
  });
}
test('API QA scripts require explicit approval before browser connection or writes',()=>{
  for(const [mode,expected] of [
    ['provision','CREATE_ISOLATED_QA_APPS'],
    ['run','RUN_ISOLATED_QA_ONLY'],
    ['auto','CREATE_AND_TEST_ISOLATED_QA']
  ]){
    const r=command(mode);
    assert.equal(r.error,undefined);
    assert.notEqual(r.status,0);
    assert.match(r.stderr,new RegExp(expected));
    assert.doesNotMatch(r.stderr,/DevToolsActivePort|Unknown tenant/i);
  }
});
test('API QA dry-run does not attach to a browser and never mutates state',()=>{
  const r=command('plan');
  assert.equal(r.status,0,r.stderr);
  const data=JSON.parse(r.stdout);
  assert.equal(data.mode,'dry-run');
  assert.equal(data.createOnly.length,3);
  assert.equal(data.safety.includes('no API writes'),true);
});
test('QA origin check prevents another tenant, protocol, or credential URL',()=>{
  assert.equal(checkedOrigin(QA_ORIGIN),QA_ORIGIN);
  const host=new URL(QA_ORIGIN).hostname;
  for(const candidate of [
    'https://unrelated.cybozu.com',
    'https://'+host+'.evil.test',
    'http://'+host,
    'https://user:password@'+host,
    'https://'+host+'/k/49/'
  ])assert.throws(()=>checkedOrigin(candidate),/restricted/);
});
