import test from 'node:test';
import assert from 'node:assert/strict';
import {strToU8,strFromU8,zipSync,unzipSync} from 'fflate';
import {makeArchive,inspectArchive,sha256} from '../src/core.js';

const fields={properties:{
  Title:{type:'SINGLE_LINE_TEXT'},
  Amount:{type:'NUMBER'},
  Choices:{type:'MULTI_SELECT'},
  Owners:{type:'USER_SELECT'},
  File:{type:'FILE'},
  Table:{type:'SUBTABLE',fields:{Memo:{type:'MULTI_LINE_TEXT'},TableFile:{type:'FILE'}}}
}};
const record={
  Title:{value:'sample'},Amount:{value:'15'},Choices:{value:['A']},
  Owners:{value:[{code:'alice'}]},File:{value:[]},
  Table:{value:[{value:{Memo:{value:'sample note'},TableFile:{value:[]}}}]}
};
async function validZip(){
  const {zip}=await makeArchive({
    appId:42,fields,records:[record],download:async()=>new Uint8Array()
  });
  return zip;
}
async function forgedRecord(mutator){
  const files=unzipSync(await validZip());
  const row=JSON.parse(strFromU8(files['data/records.jsonl']).trim());
  mutator(row);
  files['data/records.jsonl']=strToU8(JSON.stringify(row)+'\n');
  const manifest=JSON.parse(strFromU8(files['manifest.json']));
  manifest.digests['data/records.jsonl']=await sha256(files['data/records.jsonl']);
  files['manifest.json']=strToU8(JSON.stringify(manifest));
  return zipSync(files);
}

test('well-formed portable records, table rows and selection arrays remain importable',async()=>{
  const result=await inspectArchive(await validZip());
  assert.equal(result.records[0].Table.value[0].value.Memo.value,'sample note');
  assert.deepEqual(result.records[0].Owners.value,[{code:'alice'}]);
});

test('reject unknown fields and malformed scalar values despite valid internal SHA-256',async()=>{
  const cases=[
    row=>{row.Unexpected={value:'payload'};},
    row=>{row.Title.value={malicious:'object'};},
    row=>{row.Amount.value={amount:15};},
    row=>{row.Title={notValue:'text'};}
  ];
  for(const mutate of cases)
    await assert.rejects(()=>forgedRecord(mutate).then(zip=>inspectArchive(zip)),/レコード項目|文字列|数値|定義されていない/);
});

test('reject malformed multi-select and user identifiers despite matching digest',async()=>{
  for(const mutate of [
    row=>{row.Choices.value='A';},
    row=>{row.Choices.value=[55];},
    row=>{row.Owners.value=[{code:99}];},
    row=>{row.Owners.value=['alice'];}
  ])await assert.rejects(()=>forgedRecord(mutate).then(zip=>inspectArchive(zip)),/複数選択|ユーザー・組織/);
});

test('reject nested table structure corruption before record creation',async()=>{
  for(const mutate of [
    row=>{row.Table.value={};},
    row=>{row.Table.value=[{id:'old-id',value:{}}];},
    row=>{row.Table.value=[{value:{Memo:{value:{text:'x'}}}}];},
    row=>{row.Table.value=[{value:{Unknown:{value:'x'}}}];}
  ])await assert.rejects(()=>forgedRecord(mutate).then(zip=>inspectArchive(zip)),/テーブル|レコード項目|文字列/);
});

test('reject FILE values with source fileKeys, missing hashes, or wrong type',async()=>{
  for(const mutate of [
    row=>{row.File.value='not a file array';},
    row=>{row.File.value=[{fileKey:'source-key',name:'secret',size:10,contentType:'text/plain'}];},
    row=>{row.File.value=[{ref:'f'.repeat(64),fileKey:'source-key',name:'secret',size:10,contentType:'text/plain'}];},
    row=>{row.File.value=[{ref:'f'.repeat(64),name:'secret',size:'10',contentType:'text/plain'}];},
    row=>{row.Table.value[0].value.TableFile.value=[{ref:'not-a-sha',name:'a',size:0,contentType:'application/octet-stream'}];}
  ])await assert.rejects(()=>forgedRecord(mutate).then(zip=>inspectArchive(zip)),/添付ファイル/);
});
