import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const dir=await fs.mkdtemp(path.join(os.tmpdir(),'resoarc-qa-mock-'));
process.env.RESOARC_QA_STATE=path.join(dir,'isolated-qa-state.json');
const {prepare,run,loadState}=await import('../scripts/qa-api.mjs');

function fakeKintoneSession(){
  const apps=new Map(),files=new Map(),cursors=new Map(),calls=[];
  let nextApp=901,nextFile=0,nextCursor=0;
  const roleById=id=>apps.get(Number(id));
  function decoratedRecord(rec){
    const item=structuredClone(rec);
    function visit(data){
      for(const field of Object.values(data)){
        if(!field||!Object.hasOwn(field,'value'))continue;
        if(!Array.isArray(field.value))continue;
        if(field.value.some(x=>x?.fileKey)){
          field.value=field.value.map(x=>{
            const file=files.get(x.fileKey);
            if(!file)throw Error('Unknown test file');
            return {fileKey:x.fileKey,name:file.name,size:String(file.bytes.byteLength),contentType:file.type};
          });
        }else if(field.value.some(x=>x?.value))for(const row of field.value)visit(row.value);
      }
    }
    visit(item);
    return item;
  }
  const session={
    calls,apps,files,
    async sessionStatus(){return {authenticated:true,appReadable:true};},
    async upload(bytes,name,type='text/plain'){
      const key='test-file-'+(++nextFile);
      files.set(key,{bytes:Uint8Array.from(bytes),name,type});
      return key;
    },
    async download(key){
      const file=files.get(key);
      if(!file)throw Error('Missing mock file');
      return Uint8Array.from(file.bytes);
    },
    async request(route,method,arg){
      calls.push({route,method,app:arg?.app??arg?.id??null});
      if(route==='/k/v1/preview/app.json'&&method==='POST'){
        const id=nextApp++;
        apps.set(id,{id,name:arg.name,fields:null,records:[],deployed:false});
        return {app:String(id),revision:'1'};
      }
      if(route==='/k/v1/preview/app/form/fields.json'&&method==='POST'){
        const app=roleById(arg.app);
        if(!app||app.deployed)throw Error('Invalid QA fields call');
        app.fields=structuredClone(arg.properties);
        return {revision:'2'};
      }
      if(route==='/k/v1/preview/app/deploy.json'&&method==='POST'){
        for(const x of arg.apps){
          const app=roleById(x.app);
          if(!app||!app.fields)throw Error('Missing QA fields');
          app.deployed=true;
        }
        return {};
      }
      if(route==='/k/v1/preview/app/deploy.json'&&method==='GET')
        return {apps:arg.apps.map(id=>({app:String(id),status:roleById(id)?.deployed?'SUCCESS':'FAIL'}))};
      if(route==='/k/v1/app.json'&&method==='GET'){
        const app=roleById(arg.id);
        if(!app||!app.deployed)throw Error('Unknown/undeployed QA app');
        return {appId:String(app.id),name:app.name};
      }
      if(route==='/k/v1/app/form/fields.json'&&method==='GET')
        return {properties:structuredClone(roleById(arg.app).fields)};
      if(route==='/k/v1/app/form/layout.json'&&method==='GET')
        return {layout:[]};
      if(route==='/k/v1/records/cursor.json'&&method==='POST'){
        const app=roleById(arg.app);
        const id='qa-cursor-'+(++nextCursor);
        cursors.set(id,{rows:app.records.map(decoratedRecord),pos:0,size:arg.size});
        return {id};
      }
      if(route==='/k/v1/records/cursor.json'&&method==='GET'){
        const cur=cursors.get(arg.id);
        if(!cur)throw Error('Cursor does not exist');
        const result=cur.rows.slice(cur.pos,cur.pos+cur.size);
        cur.pos+=cur.size;
        const next=cur.pos<cur.rows.length;
        if(!next)cursors.delete(arg.id);
        return {records:result,next};
      }
      if(route==='/k/v1/records/cursor.json'&&method==='DELETE'){
        cursors.delete(arg.id);return {};
      }
      if(route==='/k/v1/records.json'&&method==='POST'){
        const app=roleById(arg.app);
        const used=new Set(app.records.map(r=>r.ResoArcRestoreKey?.value).filter(Boolean));
        for(const item of arg.records){
          const marker=item.ResoArcRestoreKey?.value;
          if(marker&&used.has(marker))throw Error('Duplicate restore marker');
          if(marker)used.add(marker);
        }
        app.records.push(...structuredClone(arg.records));
        return {ids:arg.records.map((_,i)=>String(app.records.length-arg.records.length+i+1))};
      }
      if(route==='/k/v1/record.json'&&method==='POST'){
        const app=roleById(arg.app);
        app.records.push(structuredClone(arg.record));
        return {id:String(app.records.length)};
      }
      throw Error('Unexpected API call '+method+' '+route);
    }
  };
  return session;
}
test('QA API runner explicitly refuses provisioning or restoring without approval',async()=>{
  const session=fakeKintoneSession();
  await assert.rejects(()=>prepare(session,'NO'),/confirm/);
  await assert.rejects(()=>run(session,'NO'),/confirm/);
  assert.equal(session.calls.length,0);
});
test('isolated QA setup and real migration code are repeatable without creating duplicates',async()=>{
  const session=fakeKintoneSession();
  const prepared=await prepare(session,'CREATE_ISOLATED_QA_APPS');
  assert.equal(Object.keys(prepared.createdTestApps).length,3);
  assert.equal(session.apps.size,3);
  const result=await run(session,'RUN_ISOLATED_QA_ONLY');
  assert.deepEqual([result.sourceRecords,result.newRecords,result.retryAdded],[3,3,0]);
  assert.equal(result.destinationRecords,3);
  assert.equal(result.attachmentHashesChecked,2);
  assert.equal(result.integrity,'PASS');
  const again=await run(session,'RUN_ISOLATED_QA_ONLY');
  assert.equal(again.zipSHA256,result.zipSHA256);
  assert.deepEqual([again.alreadyBefore,again.newRecords,again.retryAdded],[3,0,0]);
  assert.equal(again.destinationRecords,3);
  assert.equal(session.apps.get(prepared.createdTestApps.management.id).records.length,1,
    'QA management app must not store duplicate ZIP records');
  assert.equal(session.calls.filter(c=>c.method==='DELETE'||c.method==='PUT').length,0);
});
test('state tampering to redirect QA writes to another app is rejected before writes',async()=>{
  const session=fakeKintoneSession();
  const state=await loadState();
  assert.equal(state.phase,'ready');
  const old=state.apps.destination.id;
  state.apps.destination.id=999;
  await fs.writeFile(process.env.RESOARC_QA_STATE,JSON.stringify(state),'utf8');
  await assert.rejects(()=>run(session,'RUN_ISOLATED_QA_ONLY'),/Unknown|identity|app/i);
  state.apps.destination.id=old;
  await fs.writeFile(process.env.RESOARC_QA_STATE,JSON.stringify(state),'utf8');
  assert.equal(session.calls.filter(c=>c.route==='/k/v1/records.json'&&c.method==='POST').length,0);
});
test.after(async()=>{await fs.rm(dir,{recursive:true,force:true});});
