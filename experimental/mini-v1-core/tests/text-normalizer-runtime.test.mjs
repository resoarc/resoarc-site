import test from 'node:test';
import assert from 'node:assert/strict';
import {validateRules,registerTextNormalizer} from '../plugins/text-normalizer/runtime.mjs';
import {normalizeFields} from '../src/core.mjs';

test('registers four desktop/mobile submit events with valid config',()=>{
  let names,fn;const k={events:{on(events,handler){names=events;fn=handler;}}};
  assert.equal(registerTextNormalizer(k,{settings:JSON.stringify({rules:[{field:'Name',mode:'nfkc-trim'}]})},{normalizeFields}),true);
  assert.deepEqual(names,['app.record.create.submit','app.record.edit.submit','mobile.app.record.create.submit','mobile.app.record.edit.submit']);
  const event={record:{Name:{type:'SINGLE_LINE_TEXT',value:'ＡＢＣ　'},Untouched:{type:'NUMBER',value:'2'}}};
  assert.equal(fn(event).record.Name.value,'ABC');
  assert.equal(event.record.Untouched.value,'2');
});
test('malformed JSON fails closed and installs no handlers',()=>{
  let count=0;const k={events:{on(){count++}}};
  assert.equal(registerTextNormalizer(k,{settings:'{bad'}, {normalizeFields}),false);
  assert.equal(count,0);
});
test('unknown modes and duplicate fields rejected',()=>{
  assert.equal(validateRules({settings:JSON.stringify({rules:[{field:'x',mode:'code'}]})}),null);
  assert.equal(validateRules({settings:JSON.stringify({rules:[{field:'x',mode:'trim'},{field:'x',mode:'trim'}]})}),null);
});
test('text normalizer never modifies unsupported record field types',()=>{
  let cb;const k={events:{on(_,fn){cb=fn}}};
  registerTextNormalizer(k,{settings:JSON.stringify({rules:[{field:'A',mode:'trim'}]})},{normalizeFields});
  assert.equal(cb({record:{A:{type:'FILE',value:[{fileKey:'abc'}]}}}).record.A.value[0].fileKey,'abc');
});
