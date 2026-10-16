import test from 'node:test';
import assert from 'node:assert/strict';
import {makeArchive,inspectArchive} from '../src/core.js';
import {createMappedRestorePlan,runResumableRestore,MARKER_CODE,scanRestoreKeys,restoreKeyBase,keyForIndex} from '../src/restore.js';
const original={properties:{
  Title:{type:'SINGLE_LINE_TEXT',label:'title'},
  Rows:{type:'SUBTABLE',fields:{Memo:{type:'MULTI_LINE_TEXT'}}},
  File:{type:'FILE'},
}};
const target={properties:{
  Name:{type:'SINGLE_LINE_TEXT'},
  Lines:{type:'SUBTABLE',fields:{Note:{type:'MULTI_LINE_TEXT'}}},
  File:{type:'FILE'},
  ResoArcRestoreKey:{type:'SINGLE_LINE_TEXT',unique:true,required:false}
}};
const archive=async n=>{
 const records=Array.from({length:n},(_,i)=>({
   Title:{value:'Record '+i},
   Rows:{value:[{value:{Memo:{value:'line '+i}}}]},
   File:{value:[{fileKey:'sample',name:'test.txt',size:1,contentType:'text/plain'}]}
 }));
 const built=await makeArchive({appId:12,fields:original,records,download:async()=>new TextEncoder().encode('x')});
 return inspectArchive(built.zip,{expectedHash:built.hash});
};
const map={Title:'Name',Rows:'Lines','Rows.Memo':'Lines.Note'};
function mockServer({failAfterFirstWrite=false}={}){
 const records=[];
 const calls=[];
 let currentCursor=null, lost=failAfterFirstWrite;
 const api=async(path,method,body)=>{
   calls.push({path,method,body});
   if(path==='/k/v1/records/cursor.json'&&method==='POST'){
     currentCursor={id:'cursor-1',page:0};
     return {id:'cursor-1',totalCount:String(records.length)};
   }
   if(path==='/k/v1/records/cursor.json'&&method==='GET'){
     const pg=records.slice(currentCursor.page*500,(currentCursor.page+1)*500).map(row=>({
       [MARKER_CODE]:{value:row[MARKER_CODE]?.value}
     }));
     currentCursor.page++;
     return {records:pg,next:currentCursor.page*500<records.length};
   }
   if(path==='/k/v1/records/cursor.json'&&method==='DELETE')return {};
   if(path==='/k/v1/records.json'&&method==='POST'){
     for(const r of body.records){
       if(records.some(x=>x[MARKER_CODE].value===r[MARKER_CODE].value))
         throw Error('unique constraint violation');
     }
     records.push(...body.records);
     if(lost){lost=false;throw Error('network response lost');}
     return {ids:body.records.map((_,i)=>String(records.length-body.records.length+i+1))};
   }
   throw Error('unexpected '+method+' '+path);
 };
 return {api,records,calls};
}
test('maps nested table fields and retains portable FILE references',async()=>{
 const a=await archive(2);
 const plan=createMappedRestorePlan(a,target,55,99,map);
 assert.equal(plan.rows.length,2);
 assert.equal(plan.rows[0].Name.value,'Record 0');
 assert.equal(plan.rows[0].Lines.value[0].value.Note.value,'line 0');
 assert.ok(!('Title' in plan.rows[0]));
 assert.equal(plan.rows[0].File.value[0].ref.length,64);
 assert.equal(plan.markerCode,MARKER_CODE);
});
test('rejects duplicate destination mappings and invalid source paths',async()=>{
 const a=await archive(1);
 assert.throws(()=>createMappedRestorePlan(a,target,55,99,{Title:'Name','Rows':'Lines','Rows.Memo':'Lines.Note',File:'Name'}),/同じ移行先|互換性/);
 assert.throws(()=>createMappedRestorePlan(a,target,55,99,{Unknown:'Name'}),/存在しない元/);
 assert.throws(()=>createMappedRestorePlan(a,target,55,99,{Rows:'Lines','Rows.Memo':'Wrong.Note'}),/親テーブル/);
 assert.throws(()=>createMappedRestorePlan(a,target,55,99,{Title:MARKER_CODE}),/復元管理/);
});
test('requires unique single-line marker in destination',async()=>{
 const a=await archive(1);
 const without={properties:{...target.properties}};
 delete without.properties.ResoArcRestoreKey;
 assert.throws(()=>createMappedRestorePlan(a,without,55,99,map),/重複禁止/);
 const wrong={properties:{...target.properties,ResoArcRestoreKey:{type:'SINGLE_LINE_TEXT',unique:false}}};
 assert.throws(()=>createMappedRestorePlan(a,wrong,55,99,map),/重複禁止/);
});
test('resume skips committed rows after uncertain first network response',async()=>{
 const a=await archive(3);
 const plan=createMappedRestorePlan(a,target,55,99,map);
 const {api,records,calls}=mockServer({failAfterFirstWrite:true});
 const upload=async()=> 'fresh-file';
 await assert.rejects(()=>runResumableRestore({archive:a,plan,api,upload,batchSize:2}),/network response lost/);
 assert.equal(records.length,2);
 const resumed=await runResumableRestore({archive:a,plan,api,upload,batchSize:2});
 assert.deepEqual({added:resumed.added,already:resumed.already},{added:1,already:2});
 assert.equal(records.length,3);
 assert.equal(new Set(records.map(x=>x.ResoArcRestoreKey.value)).size,3);
 assert.equal(records[0].Name.value,'Record 0');
 assert.equal(records[2].Lines.value[0].value.Note.value,'line 2');
 const third=await runResumableRestore({archive:a,plan,api,upload});
 assert.equal(third.added,0);
 assert.equal(third.already,3);
 assert.equal(calls.filter(c=>c.method==='POST'&&c.path==='/k/v1/records.json').length,2);
});
test('mapping changes for same archive are refused after first migration',async()=>{
 const a=await archive(1);
 const p=createMappedRestorePlan(a,target,55,99,map);
 const {api}=mockServer();
 await runResumableRestore({archive:a,plan:p,api,upload:async()=>'uploaded'});
 const changed=createMappedRestorePlan(a,target,55,99,{...map,File:'File'});
 await assert.rejects(()=>runResumableRestore({archive:a,plan:changed,api,upload:async()=>'uploaded'}),/別のフィールド対応付け/);
});
test('keys are deterministic and distinguish source archive and mapping',async()=>{
 const a=await archive(1),plan=createMappedRestorePlan(a,target,55,99,map);
 const k=await restoreKeyBase(a,plan);
 assert.equal(k.base, (await restoreKeyBase(a,plan)).base);
 assert.notEqual(keyForIndex(k.base,0),keyForIndex(k.base,1));
 assert.ok(keyForIndex(k.base,123).length<=64);
 assert.throws(()=>keyForIndex(k.base,-1),/不正/);
});
test('failed cursor query cleanup happens without registering records',async()=>{
 const calls=[];
 const api=async(path,method,body)=>{
   calls.push([path,method]);
   if(method==='POST')return {id:'cursor'};
   if(method==='GET')throw Error('no permission');
   if(method==='DELETE')return {};
 };
 await assert.rejects(()=>scanRestoreKeys(55,api),/no permission/);
 assert.ok(calls.some(([p,m])=>p==='/k/v1/records/cursor.json'&&m==='DELETE'));
});

test('read-only preview reports completed and pending rows before any record writes',async()=>{
 const {previewRestoreProgress}=await import('../src/restore.js');
 const a=await archive(4);
 const p=createMappedRestorePlan(a,target,55,99,map);
 const env=mockServer();
 const initial=await previewRestoreProgress({archive:a,plan:p,api:env.api});
 assert.deepEqual([initial.total,initial.already,initial.remaining],[4,0,4]);
 assert.equal(env.calls.filter(c=>c.path==='/k/v1/records.json').length,0);
 await runResumableRestore({archive:a,plan:p,api:env.api,upload:async()=>'key',batchSize:3});
 const final=await previewRestoreProgress({archive:a,plan:p,api:env.api});
 assert.deepEqual([final.total,final.already,final.remaining],[4,4,0]);
});
test('equivalent JSON mapping key order has the same durable resume identity',async()=>{
 const a=await archive(1);
 const p1=createMappedRestorePlan(a,target,55,99,map);
 const p2=createMappedRestorePlan(a,target,55,99,{
   'Rows.Memo':'Lines.Note',Rows:'Lines',File:'File',Title:'Name'
 });
 const p3=createMappedRestorePlan(a,target,55,99,{
   Title:'Name','Rows.Memo':'Lines.Note',Rows:'Lines',File:'File'
 });
 const k2=(await restoreKeyBase(a,p2)).base;
 const k3=(await restoreKeyBase(a,p3)).base;
 assert.equal(k2,k3);
 assert.notEqual((await restoreKeyBase(a,p1)).base,k2);
});
test('formula-generated single line text is excluded from backups',async()=>{
 const {writableSchema}=await import('../src/core.js');
 const s=writableSchema({properties:{
   Formula:{type:'SINGLE_LINE_TEXT',expression:'Name & "!"'},
   Manual:{type:'SINGLE_LINE_TEXT',expression:''}
 }});
 assert.deepEqual(Object.keys(s),['Manual']);
});

test('destination choice validation prevents unsupported dropdown values',async()=>{
 const a=await archive(1);
 const customTarget={properties:{...target.properties,Name:{
   type:'DROP_DOWN',options:{Approved:{label:'Approved',index:'0'}}
 }}};
 assert.throws(()=>createMappedRestorePlan(a,customTarget,55,99,map),/互換性/);
 const src={properties:{Status:{type:'DROP_DOWN',options:{Old:{label:'Old',index:'0'}}}}};
 const b=await makeArchive({appId:1,fields:src,records:[{Status:{value:'Old'}}],download:async()=>new Uint8Array()});
 const x=await inspectArchive(b.zip);
 const wrong={properties:{Status:{type:'DROP_DOWN',options:{New:{label:'New',index:'0'}}},ResoArcRestoreKey:target.properties.ResoArcRestoreKey}};
 assert.throws(()=>createMappedRestorePlan(x,wrong,55,99,{}),/選択肢に存在しない値/);
});
test('destination required fields missing from source are rejected before upload',async()=>{
 const a=await archive(1);
 const destination={properties:{...target.properties,MustSet:{type:'SINGLE_LINE_TEXT',required:true}}};
 assert.throws(()=>createMappedRestorePlan(a,destination,55,99,map),/未対応の必須フィールド/);
});