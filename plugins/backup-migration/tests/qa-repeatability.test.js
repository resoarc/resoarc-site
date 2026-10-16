import test from 'node:test';
import assert from 'node:assert/strict';
import {makeArchive,inspectArchive} from '../src/core.js';

const fixture={
  appId:424,
  fields:{properties:{
    Title:{type:'SINGLE_LINE_TEXT'},
    Notes:{type:'SUBTABLE',fields:{Memo:{type:'MULTI_LINE_TEXT'}}}
  }},
  layout:{layout:[]},
  records:[{
    Title:{value:'Repeatability'},
    Notes:{value:[{value:{Memo:{value:'Testing the same archive twice'}}}]}
  }],
  now:'2026-10-16T10:00:00.000Z',
  download:async()=>new Uint8Array()
};
test('a fixed archive timestamp yields reproducible hashes after time passes',async()=>{
  const first=await makeArchive(fixture);
  // ZIP entry timestamps traditionally depend on current time, even if the
  // manifest has fixed createdAt. Cross a DOS ZIP timestamp boundary.
  await new Promise(resolve=>setTimeout(resolve,2250));
  const second=await makeArchive(fixture);
  assert.deepEqual(first.zip,second.zip);
  assert.equal(first.hash,second.hash);
  assert.equal((await inspectArchive(second.zip)).records[0].Title.value,'Repeatability');
});
test('reject archive timestamps outside ZIP supported range',async()=>{
  for(const now of ['1970-01-01T00:00:00Z','2108-01-01T00:00:00Z','invalid']){
    await assert.rejects(()=>makeArchive({...fixture,now}),/日時が不正/);
  }
});
