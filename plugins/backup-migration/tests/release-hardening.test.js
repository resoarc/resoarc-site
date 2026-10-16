import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchAllRecords} from '../src/transport.js';
import {scanRestoreKeys,MARKER_CODE,createMappedRestorePlan,runResumableRestore} from '../src/restore.js';
import {makeArchive,inspectArchive,writableSchema} from '../src/core.js';

function cursorApi(pages) {
  const calls=[];
  let page=0;
  const api=async(path,method,body)=>{
    calls.push({path,method,body});
    if(method==='POST' && path==='/k/v1/records/cursor.json') return {id:'cursor-7'};
    if(method==='GET' && path==='/k/v1/records/cursor.json') {
      const value=pages[page++];
      if(value instanceof Error) throw value;
      return value;
    }
    if(method==='DELETE' && path==='/k/v1/records/cursor.json') return {};
    throw Error('unexpected API '+method+' '+path);
  };
  return {api,calls};
}
const isDelete=c=>c.method==='DELETE' && c.path==='/k/v1/records/cursor.json';

test('backup cursor reads 500+ records across multiple pages without writing records',async()=>{
 const p=cursorApi([{records:Array.from({length:500},(_,i)=>({id:i})),next:true},
                    {records:[{id:500}],next:false}]);
 const rows=await fetchAllRecords(42,p.api);
 assert.equal(rows.length,501);
 assert.equal(rows[500].id,500);
 assert.deepEqual(p.calls.map(c=>c.method),['POST','GET','GET']);
 assert.equal(p.calls.filter(isDelete).length,0);
});
test('backup cursor rejects empty continuing page and cleans up',async()=>{
 const p=cursorApi([{records:[],next:true}]);
 await assert.rejects(()=>fetchAllRecords(42,p.api),/進行しません/);
 assert.equal(p.calls.filter(isDelete).length,1);
});
test('backup cursor enforces max records before accumulating oversized page',async()=>{
 const p=cursorApi([{records:[{id:1},{id:2}],next:false}]);
 await assert.rejects(()=>fetchAllRecords(42,p.api,{maxRecords:1}),/上限|件まで/);
 assert.equal(p.calls.filter(isDelete).length,1);
});
test('backup cursor cleans up on network failure after successful page',async()=>{
 const p=cursorApi([{records:[{id:1}],next:true},new Error('transient network failure')]);
 await assert.rejects(()=>fetchAllRecords(42,p.api),/transient/);
 assert.equal(p.calls.filter(isDelete).length,1);
});
test('backup cursor rejects invalid pagination response and cleans up',async()=>{
 const p=cursorApi([{records:[],next:'false'}]);
 await assert.rejects(()=>fetchAllRecords(42,p.api),/取得結果が不正/);
 assert.equal(p.calls.filter(isDelete).length,1);
});
test('restore cursor rejects stalled page and never issues record writes',async()=>{
 const p=cursorApi([{records:[],next:true}]);
 await assert.rejects(()=>scanRestoreKeys(81,p.api),/進行しません/);
 assert.equal(p.calls.filter(isDelete).length,1);
 assert.equal(p.calls.filter(c=>c.path==='/k/v1/records.json').length,0);
});
test('restore cursor rejects excessive or malformed cursor response',async()=>{
 const p=cursorApi([{records:Array.from({length:501},()=>({[MARKER_CODE]:{value:'a'}})),next:false}]);
 await assert.rejects(()=>scanRestoreKeys(81,p.api),/取得結果が不正/);
 assert.equal(p.calls.filter(isDelete).length,1);
});
test('resume preview/restore cannot write if cursor fails',async()=>{
 const data=await makeArchive({appId:12,fields:{properties:{Title:{type:'SINGLE_LINE_TEXT'}}},records:[{Title:{value:'a'}}],download:async()=>new Uint8Array()});
 const archive=await inspectArchive(data.zip);
 const target={properties:{Title:{type:'SINGLE_LINE_TEXT'},[MARKER_CODE]:{type:'SINGLE_LINE_TEXT',unique:true}}};
 const plan=createMappedRestorePlan(archive,target,81,99);
 const p=cursorApi([{records:[],next:true}]);
 let uploads=0;
 await assert.rejects(()=>runResumableRestore({archive,plan,api:p.api,upload:async()=>{uploads++; return 'x';}}),/進行しません/);
 assert.equal(uploads,0);
 assert.equal(p.calls.filter(c=>c.path==='/k/v1/records.json').length,0);
});

test('refuses reserved prototype-property field codes in new backups',async()=>{
 const source=JSON.parse('{"__proto__":{"type":"SINGLE_LINE_TEXT"}}');
 assert.throws(()=>writableSchema({properties:source}),/予約済み/);
 await assert.rejects(()=>makeArchive({appId:12,fields:{properties:source},records:[],download:async()=>new Uint8Array()}),/予約済み/);
});
test('rejects legacy ZIP with unsafe or unknown portable schema definitions',async()=>{
 const {zipSync,strToU8,unzipSync}=await import('fflate');
 const {sha256}=await import('../src/core.js');
 const build=await makeArchive({appId:12,fields:{properties:{Title:{type:'SINGLE_LINE_TEXT'}}},records:[],download:async()=>new Uint8Array()});
 for (const schema of [
   JSON.parse('{"__proto__":{"type":"SINGLE_LINE_TEXT"}}'),
   {Untrusted:{type:'ADMIN_PRIVILEGE'}},
   {Table:{type:'SUBTABLE',fields:{Nested:{type:'SUBTABLE',fields:{Memo:{type:'SINGLE_LINE_TEXT'}}}}}}
 ]) {
   const files=unzipSync(build.zip);
   const manifest=JSON.parse(new TextDecoder().decode(files['manifest.json']));
   manifest.version=1;
   delete manifest.digests['schema/source-fields.json'];
   delete files['schema/source-fields.json'];
   files['schema/fields.json']=strToU8(JSON.stringify(schema));
   manifest.digests['schema/fields.json']=await sha256(files['schema/fields.json']);
   files['manifest.json']=strToU8(JSON.stringify(manifest));
   await assert.rejects(()=>inspectArchive(zipSync(files)),/不正|未対応/);
 }
});

test('new-app planner skips field codes that kintone cannot create',async()=>{
 const {planNewApp}=await import('../src/migration.js');
 const a={manifest:{version:2,sourceAppId:42},schema:{},records:[],
   sourceFields:{properties:{
     'Starts-With-Dash':{type:'SINGLE_LINE_TEXT',label:'invalid symbol'},
     '1stField':{type:'NUMBER',label:'invalid first character'},
     'Valid_名前':{type:'SINGLE_LINE_TEXT',label:'valid Japanese code'}
   }}};
 const plan=planNewApp(a,'Safe Draft');
 assert.deepEqual(Object.keys(plan.properties),['Valid_名前',MARKER_CODE]);
 assert.equal(plan.skipped.length,2);
});

test('malformed ZIP64 sentinel completes within a child-process timeout',async()=>{
  // Run the parser in an isolated process so a future decompression regression
  // cannot hang the entire test suite when fed an untrusted ZIP.
  const {spawnSync}=await import('node:child_process');
  const script=`
    import {zipSync,unzipSync,strToU8} from 'fflate';
    const z=zipSync({'manifest.json':strToU8('x')});
    const d=Uint8Array.from(z);
    let index=-1;
    for(let i=0;i<d.length-4;i++)
      if(d[i]===0x50&&d[i+1]===0x4b&&d[i+2]===0x01&&d[i+3]===0x02){index=i;break;}
    if(index<0)process.exit(7);
    d.fill(0xff,index+20,index+24); // central-directory ZIP64-size sentinel
    try{unzipSync(d);process.exit(8);}catch{process.exit(0);}
  `;
  const response=spawnSync(process.execPath,['--input-type=module','--eval',script],{
    encoding:'utf8',cwd:process.cwd(),timeout:4000
  });
  assert.equal(response.error,undefined,'ZIP parsing must not hang');
  assert.ok([0,8].includes(response.status),'ZIP parser must terminate without hanging');
});
