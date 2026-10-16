import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchAllRecords} from '../src/transport.js';
import {makeArchive,inspectArchive} from '../src/core.js';
import {planNewApp,createDraftApp} from '../src/migration.js';
import {createMappedRestorePlan,previewRestoreProgress,runResumableRestore,MARKER_CODE} from '../src/restore.js';

test('501-record full API simulation: ZIP, nested tables, draft, uncertain write, resume and no duplicates',async()=>{
  const sourceFields={properties:{
    Title:{type:'SINGLE_LINE_TEXT',code:'Title',label:'Title'},
    Amount:{type:'NUMBER',code:'Amount',label:'Amount'},
    Notes:{type:'SUBTABLE',code:'Notes',label:'Notes',fields:{
      Memo:{type:'MULTI_LINE_TEXT',code:'Memo',label:'Memo'},
      Attachment:{type:'FILE',code:'Attachment',label:'Attachment'}
    }}
  }};
  const sourceRows=Array.from({length:501},(_,i)=>({
    Title:{value:'Record '+i},Amount:{value:String(i)},
    Notes:{value:[{value:{
      Memo:{value:'Long-lived note '+i},
      Attachment:{value:[{fileKey:'shared-file',name:'note.txt',size:'4',contentType:'text/plain'}]}
    }}]}
  }));
  const state={targetRows:[],draftFields:null,draftApp:0,uploaded:0,downloaded:0,writeCalls:0,simulateLost:true,cursors:new Map(),cursorSeq:0, calls:[]};
  const api=async(path,method,body)=>{
    state.calls.push({path,method,app:body.app});
    if(path==='/k/v1/records/cursor.json' && method==='POST'){
      const id='cursor-'+(++state.cursorSeq);
      const snapshot=body.app===10?sourceRows:state.targetRows;
      state.cursors.set(id,{records:[...snapshot],page:0,size:body.size});
      return {id,totalCount:String(snapshot.length)};
    }
    if(path==='/k/v1/records/cursor.json' && method==='GET'){
      const cur=state.cursors.get(body.id);
      if(!cur)throw Error('cursor not found');
      const records=cur.records.slice(cur.page,cur.page+cur.size);
      cur.page+=cur.size;
      const next=cur.page<cur.records.length;
      if(!next)state.cursors.delete(body.id);
      return {records,next};
    }
    if(path==='/k/v1/records/cursor.json' && method==='DELETE'){
      state.cursors.delete(body.id);return {};
    }
    if(path==='/k/v1/preview/app.json' && method==='POST'){
      state.draftApp=55;return {app:'55'};
    }
    if(path==='/k/v1/preview/app/form/fields.json' && method==='POST'){
      if(body.app!==55)throw Error('wrong draft');
      state.draftFields=structuredClone(body.properties);return {revision:'1'};
    }
    if(path==='/k/v1/records.json' && method==='POST'){
      if(body.app!==55)throw Error('unsafe destination');
      const current=new Set(state.targetRows.map(x=>x[MARKER_CODE].value));
      for(const r of body.records) {
        if(current.has(r[MARKER_CODE].value))throw Error('duplicate marker');
        current.add(r[MARKER_CODE].value);
      }
      state.targetRows.push(...structuredClone(body.records));
      state.writeCalls++;
      if(state.simulateLost){state.simulateLost=false;throw Error('HTTP response lost after commit');}
      return {ids:body.records.map((_,i)=>String(state.targetRows.length-body.records.length+i+1))};
    }
    throw Error('Unexpected API: '+method+' '+path);
  };
  const source=await fetchAllRecords(10,api);
  assert.equal(source.length,501);
  const {zip,hash}=await makeArchive({appId:10,fields:sourceFields,layout:{layout:[]},records:source,
    download:async key=>{assert.equal(key,'shared-file');state.downloaded++;return new TextEncoder().encode('data');}});
  assert.equal(state.downloaded,1,'deduplicate identical source file keys');
  const a=await inspectArchive(zip,{expectedHash:hash});
  assert.equal(a.manifest.recordCount,501);
  assert.equal(a.manifest.files.length,1);
  assert.equal(a.records[500].Notes.value[0].value.Memo.value,'Long-lived note 500');
  const newApp=planNewApp(a,'ResoArc isolated test app');
  const draft=await createDraftApp(newApp,api);
  assert.equal(draft.appId,55);
  assert.equal(draft.requiresManualDeploy,true);
  assert.equal(state.draftFields[MARKER_CODE].unique,true);
  const fields={properties:state.draftFields};
  const plan=createMappedRestorePlan(a,fields,55,99);
  const before=await previewRestoreProgress({archive:a,plan,api});
  assert.equal(before.remaining,501);
  assert.equal(state.targetRows.length,0);
  const upload=async(bytes,name)=>{
    assert.equal(new TextDecoder().decode(bytes),'data');
    assert.equal(name,'note.txt');
    state.uploaded++;return 'new-file-'+state.uploaded;
  };
  await assert.rejects(()=>runResumableRestore({archive:a,plan,api,upload,batchSize:50}),/HTTP response lost/);
  assert.equal(state.targetRows.length,50);
  const afterLost=await previewRestoreProgress({archive:a,plan,api});
  assert.deepEqual([afterLost.already,afterLost.remaining],[50,451]);
  const resumed=await runResumableRestore({archive:a,plan,api,upload,batchSize:50});
  assert.equal(resumed.added,451);
  assert.equal(resumed.already,50);
  assert.equal(state.targetRows.length,501);
  assert.equal(new Set(state.targetRows.map(r=>r[MARKER_CODE].value)).size,501);
  assert.equal(state.targetRows[500].Notes.value[0].value.Memo.value,'Long-lived note 500');
  assert.ok(state.targetRows[0].Notes.value[0].value.Attachment.value[0].fileKey.startsWith('new-file-'));
  const repeat=await runResumableRestore({archive:a,plan,api,upload});
  assert.deepEqual([repeat.added,repeat.already],[0,501]);
  assert.equal(state.targetRows.length,501);
  assert.equal(state.calls.filter(c=>c.path==='/k/v1/records.json'&&c.method==='POST').length,11);
  assert.equal(state.calls.filter(c=>c.method==='PUT'||c.method==='DELETE').length,0);
});
