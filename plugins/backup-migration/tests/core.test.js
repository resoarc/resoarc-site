import test from 'node:test';
import assert from 'node:assert/strict';
import {strToU8,unzipSync,zipSync} from 'fflate';
import {makeArchive,inspectArchive,createRestorePlan,materializeRestoreRow,writableSchema,sha256} from '../src/core.js';

const fields={properties:{
  Title:{type:'SINGLE_LINE_TEXT'},
  Amount:{type:'NUMBER'},
  Owner:{type:'USER_SELECT'},
  File:{type:'FILE'},
  Calculated:{type:'CALC'},
  Lookup:{type:'SINGLE_LINE_TEXT',lookup:{relatedApp:{app:12}}},
  Table:{type:'SUBTABLE',fields:{Memo:{type:'MULTI_LINE_TEXT'},FileInTable:{type:'FILE'},Derived:{type:'CALC'}}}
}};
const getRecords=()=>[{
 '$id':{type:'__ID__',value:'99'},
 Title:{type:'SINGLE_LINE_TEXT',value:'日本語 test'},
 Amount:{type:'NUMBER',value:'120'},
 Owner:{type:'USER_SELECT',value:[{code:'alice',name:'Alice'}]},
 File:{type:'FILE',value:[{fileKey:'top',name:'top.txt',size:'4',contentType:'text/plain'}]},
 Calculated:{type:'CALC',value:'121'},
 Lookup:{type:'SINGLE_LINE_TEXT',value:'external'},
 Table:{type:'SUBTABLE',value:[{id:'19',value:{
   Memo:{type:'MULTI_LINE_TEXT',value:'table note'},
   FileInTable:{type:'FILE',value:[{fileKey:'nested',name:'inner.txt',size:'5',contentType:'text/plain'}]},
   Derived:{type:'CALC',value:'ignored'}
 }}]}
}];
async function fixture(){
 const payload={top:strToU8('top!'),nested:strToU8('inner')};
 return makeArchive({appId:42,fields,layout:{layout:[]},records:getRecords(),now:'2026-10-16T01:00:00Z',download:async key=>payload[key]});
}
test('schema filters immutable, computed and lookup fields',()=>{
 const schema=writableSchema(fields);
 assert.deepEqual(Object.keys(schema),['Title','Amount','Owner','File','Table']);
 assert.deepEqual(Object.keys(schema.Table.fields),['Memo','FileInTable']);
});
test('roundtrip portable ZIP, hash, attachments and table structure',async()=>{
 const {zip,manifest,hash}=await fixture();
 assert.equal(await sha256(zip),hash);
 assert.equal(manifest.recordCount,1);
 assert.equal(manifest.files.length,2);
 const a=await inspectArchive(zip,{expectedHash:hash});
 const row=a.records[0];
 assert.equal(row.Title.value,'日本語 test');
 assert.equal(row.Owner.value[0].code,'alice');
 assert.ok(!('Lookup' in row));
 assert.ok(!('$id' in row));
 assert.ok(!('Calculated' in row));
 assert.equal(row.Table.value[0].value.Memo.value,'table note');
 assert.ok(!('Derived' in row.Table.value[0].value));
 assert.equal(row.Table.value[0].value.FileInTable.value[0].ref.length,64);
 const plan=createRestorePlan(a,fields,89,777);
 assert.equal(plan.recordCount,1);
 const calls=[];
 const materialized=await materializeRestoreRow(plan.rows[0],plan.mapped,async(bytes,name,type)=>{
   calls.push({text:new TextDecoder().decode(bytes),name,type}); return 'new-key-'+calls.length;
 },a.files);
 assert.equal(calls.length,2);
 assert.deepEqual(calls.map(x=>x.text).sort(),['inner','top!']);
 assert.equal(materialized.File.value[0].fileKey,'new-key-1');
 assert.equal(materialized.Table.value[0].value.FileInTable.value[0].fileKey,'new-key-2');
 assert.ok(!('ref' in materialized.File.value[0]));
});
test('ZIP full checksum mismatch rejected',async()=>{
 const a=await fixture();
 await assert.rejects(()=>inspectArchive(a.zip,{expectedHash:'0'.repeat(64)}),/SHA-256/);
});
test('ZIP internally tampered schema rejected even without expected outer hash',async()=>{
 const a=await fixture();
 const entries=unzipSync(a.zip);
 entries['schema/fields.json']=strToU8('{"hacked":{"type":"FILE"}}');
 const corrupt=zipSync(entries);
 await assert.rejects(()=>inspectArchive(corrupt),/ハッシュ/);
});
test('reject incompatible destination types and destination management app',async()=>{
 const a=await inspectArchive((await fixture()).zip);
 assert.throws(()=>createRestorePlan(a,{properties:{...fields.properties,Title:{type:'NUMBER'}}},88,777),/互換性/);
 assert.throws(()=>createRestorePlan(a,fields,777,777),/管理アプリ/);
});
test('warn skipped fields but allow an append-only compatible subset',async()=>{
 const a=await inspectArchive((await fixture()).zip);
 const plan=createRestorePlan(a,{properties:{Title:{type:'SINGLE_LINE_TEXT'}}},85,99);
 assert.ok(plan.skipped.some(x=>x.includes('Table')));
 assert.deepEqual(plan.rows[0],{Title:{value:'日本語 test'}});
});
test('bounds, unresolved attachments and malformed archive rejected',async()=>{
 await assert.rejects(()=>makeArchive({appId:42,fields,records:getRecords(),download:async()=>new Uint8Array(50),maxBytes:32}),/容量上限/);
 const a=await fixture();
 await assert.rejects(()=>inspectArchive(a.zip,{maxBytes:32}),/容量上限/);
});

test('reject unexpected ZIP paths including traversal names',async()=>{
 const encoded=zipSync({'../manifest.json':strToU8('invalid')});
 await assert.rejects(()=>inspectArchive(encoded),/不正なパス/);
});
test('reject very highly compressed oversized data before extraction',async()=>{
 const bomb=zipSync({['attachments/'+ 'a'.repeat(64)]:new Uint8Array(26*1024*1024)},{level:9});
 await assert.rejects(()=>inspectArchive(bomb),/容量上限/);
});
