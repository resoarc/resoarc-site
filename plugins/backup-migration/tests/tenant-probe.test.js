import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const script=fileURLToPath(new URL('../scripts/tenant-api-probe.mjs',import.meta.url));
function probe(origin,app){
  return spawnSync(process.execPath,[script,'--origin',origin,'--app',app],{
    encoding:'utf8',timeout:5000
  });
}
test('read-only tenant probe refuses insecure, cross-domain, and credential-bearing origins',()=>{
  for(const badOrigin of [
    'http://test.cybozu.com',
    'https://test.cybozu.com.evil.example',
    'https://example.com',
    'https://user:password@test.cybozu.com',
    'https://test.cybozu.com/some-path',
    'https://test.cybozu.com/?token=leak'
  ]){
    const response=probe(badOrigin,'49');
    assert.equal(response.error,undefined,badOrigin);
    assert.notEqual(response.status,0,badOrigin);
    assert.match(response.stderr,/HTTPS cybozu tenant origin/,badOrigin);
    assert.doesNotMatch(response.stderr,/DevToolsActivePort/,'must reject before reading browser files');
  }
});
test('read-only tenant probe refuses invalid app IDs before browser access',()=>{
  for(const badApp of ['0','-5','1.3','NaN','9007199254740993']){
    const response=probe('https://test.cybozu.com',badApp);
    assert.equal(response.error,undefined,badApp);
    assert.notEqual(response.status,0,badApp);
    assert.match(response.stderr,/Positive kintone app ID required/,badApp);
    assert.doesNotMatch(response.stderr,/DevToolsActivePort/,'must reject before browser access');
  }
});
