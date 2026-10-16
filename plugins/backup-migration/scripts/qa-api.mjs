// kintone isolated test-app API suite; all API calls use the logged-in QA Edge.
// No credentials, cookies, business-app writes, or real customer records.
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {randomBytes} from 'node:crypto';
import {connectQA,QA_ORIGIN,QA_STATE,QA_APP_PROBE} from './qa-session.mjs';
import {makeArchive,inspectArchive,sha256} from '../src/core.js';
import {fetchAllRecords} from '../src/transport.js';
import {createMappedRestorePlan,previewRestoreProgress,runResumableRestore,MARKER_CODE} from '../src/restore.js';

const roles=['source','destination','management'];
const command=process.argv[2]||'status';
const confirm=process.argv.includes('--confirm')?process.argv[process.argv.indexOf('--confirm')+1]:null;
const output=obj=>console.log(JSON.stringify(obj,null,2));
const fail=message=>{throw Error(message);};
const one=(code,type,label,other={})=>({code,type,label,...other});
const testFields={
  source:{
    Title:one('Title','SINGLE_LINE_TEXT','QA title'),
    Amount:one('Amount','NUMBER','QA amount'),
    QAChoice:one('QAChoice','DROP_DOWN','QA choice',{options:{
      Alpha:{label:'Alpha',index:'0'},Beta:{label:'Beta',index:'1'}
    }}),
    Attachment:one('Attachment','FILE','QA file'),
    Notes:one('Notes','SUBTABLE','QA table',{fields:{
      Memo:one('Memo','MULTI_LINE_TEXT','QA memo'),
      NestedAttachment:one('NestedAttachment','FILE','QA nested file')
    }})
  },
  management:{
    BackupName:one('BackupName','SINGLE_LINE_TEXT','Backup Name'),
    SourceAppId:one('SourceAppId','NUMBER','Source App ID'),
    ArchiveHash:one('ArchiveHash','SINGLE_LINE_TEXT','ZIP hash'),
    BackupVersion:one('BackupVersion','SINGLE_LINE_TEXT','ZIP version'),
    RecordCount:one('RecordCount','NUMBER','Record count'),
    Archive:one('Archive','FILE','Backup ZIP')
  }
};
testFields.destination={...testFields.source,[MARKER_CODE]:one(MARKER_CODE,'SINGLE_LINE_TEXT','Restore identity',{unique:true,maxLength:'64'})};

async function loadState(){
  try{
    const state=JSON.parse(await fs.readFile(QA_STATE,'utf8'));
    if(state.version!==1||state.origin!==QA_ORIGIN||!/^ResoArc QA [0-9a-f]{10}$/.test(state.prefix))
      fail('QA test app state fails strict origin/name checks');
    return state;
  }catch(error){
    if(error.code==='ENOENT')return null;
    throw error;
  }
}
async function saveState(state){
  await fs.mkdir(path.dirname(QA_STATE),{recursive:true});
  const temporary=QA_STATE+'.pending';
  await fs.writeFile(temporary,JSON.stringify(state,null,2)+'\n',{mode:0o600});
  await fs.rename(temporary,QA_STATE);
}
function assertAppIds(state){
  if(!state||state.phase!=='ready')fail('QA test apps are not prepared. Run qa:plan and then qa:provision.');
  const ids=roles.map(role=>Number(state.apps?.[role]?.id));
  if(ids.some(id=>!Number.isSafeInteger(id)||id<1)||new Set(ids).size!==3)fail('QA app IDs are invalid or repeated');
}
async function assertIsolated(session,state){
  assertAppIds(state);
  for(const role of roles){
    const actual=await session.request('/k/v1/app.json','GET',{id:state.apps[role].id});
    if(String(actual.appId)!==String(state.apps[role].id)||actual.name!==state.apps[role].name||
       !actual.name.startsWith(state.prefix+' '))
      fail('Refusing writes: QA '+role+' app identity no longer matches recorded ID and name');
  }
  const fields=await session.request('/k/v1/app/form/fields.json','GET',{app:state.apps.destination.id});
  const marker=fields.properties?.[MARKER_CODE];
  if(marker?.unique!==true||marker.type!=='SINGLE_LINE_TEXT')
    fail('Destination QA app must have a unique single-line restore marker');
  return fields;
}
const appApi=(session)=>(route,method,args)=>session.request(route,method,args);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function prepare(session,approval=confirm){
  if(approval!=='CREATE_ISOLATED_QA_APPS')fail('Provisioning requires --confirm CREATE_ISOLATED_QA_APPS');
  const current=await loadState();
  if(current)fail('QA state already exists; refusing duplicate app creation. State: '+QA_STATE);
  const login=await session.sessionStatus(QA_APP_PROBE);
  if(!login.authenticated)fail('Sign in using the visible QA Edge first (read-only app and field checks must return 200)');
  const prefix='ResoArc QA '+randomBytes(5).toString('hex');
  const state={version:1,origin:QA_ORIGIN,prefix,phase:'creating',createdAt:new Date().toISOString(),
    fixedArchiveTime:new Date().toISOString(),apps:{}};
  // Check the destination/management names before any writes; these names
  // are only generated here, never supplied by a caller.
  for(const role of roles){
    const name=prefix+' '+role;
    const created=await session.request('/k/v1/preview/app.json','POST',{name});
    if(!/^[0-9]+$/.test(String(created?.app||'')))fail('QA app create returned no app ID');
    state.apps[role]={id:Number(created.app),name};
    await saveState(state); // retain ID even if field/deploy setup fails
    await session.request('/k/v1/preview/app/form/fields.json','POST',{
      app:Number(created.app),properties:testFields[role]
    });
  }
  const ids=roles.map(role=>({app:state.apps[role].id}));
  await session.request('/k/v1/preview/app/deploy.json','POST',{apps:ids,revert:false});
  let statuses=[];
  for(let attempt=0;attempt<40;attempt++){
    const status=await session.request('/k/v1/preview/app/deploy.json','GET',{
      apps:ids.map(v=>v.app)
    });
    statuses=status.apps||[];
    if(statuses.length===3&&statuses.every(s=>s.status==='SUCCESS'))break;
    if(statuses.some(s=>['FAIL','CANCEL'].includes(s.status)))fail('QA app deployment failed: '+JSON.stringify(statuses.map(s=>s.status)));
    await sleep(600);
  }
  if(statuses.length!==3||!statuses.every(s=>s.status==='SUCCESS'))
    fail('QA deployment is not complete. App IDs saved for inspection; do not reprovision.');
  state.phase='ready';state.deployedAt=new Date().toISOString();
  await saveState(state);
  await assertIsolated(session,state);
  return {createdTestApps:state.apps,origin:state.origin,profile:'visible QA Edge',statePath:QA_STATE};
}
async function seed(session,state){
  const source=state.apps.source.id;
  const api=appApi(session);
  const existing=await fetchAllRecords(source,api,{maxRecords:100});
  if(existing.length!==0){
    if(existing.length!==3)fail('QA source has an unexpected number of records: '+existing.length);
    const values=existing.map(r=>r.Title?.value);
    if(values.some((v,i)=>v!==state.prefix+' row '+(i+1)))fail('QA source contains unrecognized records; refusing to operate');
    return {created:false,count:existing.length};
  }
  const data=new TextEncoder().encode('ResoArc QA attachment '+state.prefix);
  const top=await session.upload(data,'qa-main.txt');
  const nested=await session.upload(data,'qa-nested.txt');
  const records=Array.from({length:3},(_,i)=>({
    Title:{value:state.prefix+' row '+(i+1)},
    Amount:{value:String((i+1)*100)},
    QAChoice:{value:i%2?'Beta':'Alpha'},
    Attachment:{value:i===0?[{fileKey:top}]:[]},
    Notes:{value:[{value:{
      Memo:{value:'QA memo '+(i+1)},
      NestedAttachment:{value:i===0?[{fileKey:nested}]:[]}
    }}]}
  }));
  const done=await api('/k/v1/records.json','POST',{app:source,records});
  if(!Array.isArray(done.ids)||done.ids.length!==records.length)
    fail('QA source fixture write returned an unexpected number of IDs');
  return {created:true,count:records.length};
}
async function run(session,approval=confirm){
  if(approval!=='RUN_ISOLATED_QA_ONLY')fail('Integration tests require --confirm RUN_ISOLATED_QA_ONLY');
  const state=await loadState();
  await assertIsolated(session,state);
  const api=appApi(session);
  const initial=await seed(session,state);
  const fields=await api('/k/v1/app/form/fields.json','GET',{app:state.apps.source.id});
  const layout=await api('/k/v1/app/form/layout.json','GET',{app:state.apps.source.id});
  const records=await fetchAllRecords(state.apps.source.id,api,{maxRecords:100});
  if(records.length!==3)fail('Source QA fixture count unexpectedly changed');
  const backup=await makeArchive({
    appId:state.apps.source.id,fields,layout,records,now:state.fixedArchiveTime,
    download:key=>session.download(key)
  });
  const archive=await inspectArchive(backup.zip,{expectedHash:backup.hash});
  // Both QA attachment fields use the same bytes. The archive deliberately
  // deduplicates them into one content-addressed payload.
  if(archive.manifest.recordCount!==3||archive.manifest.files.length!==1)
    fail('Actual QA ZIP did not contain three records and one deduplicated attachment');
  // Management record is generated only for this isolated QA app, not a
  // user-supplied app ID. Keep one record per deterministic archive hash.
  const mgmt=state.apps.management.id;
  const saved=await fetchAllRecords(mgmt,api,{maxRecords:100});
  const duplicates=saved.filter(r=>r.ArchiveHash?.value===backup.hash);
  if(duplicates.length>1)fail('More than one management record references the QA ZIP');
  if(!duplicates.length){
    const key=await session.upload(backup.zip,'resoarc-qa-'+state.prefix+'.zip','application/zip');
    await api('/k/v1/record.json','POST',{app:mgmt,record:{
      BackupName:{value:state.prefix},
      SourceAppId:{value:String(state.apps.source.id)},
      ArchiveHash:{value:backup.hash},
      BackupVersion:{value:String(archive.manifest.version)},
      RecordCount:{value:'3'},
      Archive:{value:[{fileKey:key}]}
    }});
  }
  // Read back through the live management app and independently check hashes.
  const savedRecords=await fetchAllRecords(mgmt,api,{maxRecords:100});
  const stored=savedRecords.find(r=>r.ArchiveHash?.value===backup.hash);
  if(!stored)fail('QA management record is missing');
  const blob=stored.Archive?.value?.[0];
  if(!blob?.fileKey)fail('QA management attachment is missing');
  const retrieved=await session.download(blob.fileKey);
  if(await sha256(retrieved)!==backup.hash)fail('QA management ZIP SHA-256 round-trip mismatch');
  const checked=await inspectArchive(retrieved,{expectedHash:backup.hash});
  const target=await api('/k/v1/app/form/fields.json','GET',{app:state.apps.destination.id});
  const plan=createMappedRestorePlan(checked,target,state.apps.destination.id,mgmt);
  const before=await previewRestoreProgress({archive:checked,plan,api});
  const first=await runResumableRestore({archive:checked,plan,api,
    upload:(bytes,name,type)=>session.upload(bytes,name,type),batchSize:2});
  const second=await runResumableRestore({archive:checked,plan,api,
    upload:(bytes,name,type)=>session.upload(bytes,name,type),batchSize:2});
  if(before.remaining!==first.added||second.added!==0||second.already!==3)
    fail('QA restore counts or idempotency check failed');
  const restored=await fetchAllRecords(state.apps.destination.id,api,{maxRecords:100});
  if(restored.length!==3)fail('QA destination record count is not three');
  const sample=r=>({
    title:r.Title.value,amount:r.Amount.value,choice:r.QAChoice.value,
    memo:r.Notes.value[0].value.Memo.value
  });
  const byTitle=(a,b)=>a.title.localeCompare(b.title,'en');
  const original=records.map(sample).sort(byTitle);
  const actual=restored.map(sample).sort(byTitle);
  if(JSON.stringify(original)!==JSON.stringify(actual))fail('QA restored scalar/table values differ from source');
  // Check binary attachments after restore, in both main and nested fields.
  for(const field of ['Attachment','NestedAttachment']){
    const firstRecord=restored[0];
    const file=field==='Attachment'?firstRecord.Attachment?.value?.[0]:
      firstRecord.Notes?.value?.[0]?.value?.NestedAttachment?.value?.[0];
    if(!file?.fileKey)fail('QA restored '+field+' attachment is missing');
    const restoredBytes=await session.download(file.fileKey);
    if(new TextDecoder().decode(restoredBytes)!=='ResoArc QA attachment '+state.prefix)
      fail('QA restored '+field+' attachment bytes mismatch');
  }
  return {
    ok:true,origin:state.origin,sourceApp:state.apps.source.id,destinationApp:state.apps.destination.id,
    managementApp:mgmt,sourceRecords:records.length,zipSHA256:backup.hash,
    zipBytes:backup.zip.length,attachmentHashesChecked:2,createdFixture:initial.created,
    alreadyBefore:before.already,newRecords:first.added,retryAdded:second.added,
    destinationRecords:restored.length,integrity:'PASS',restoreIdempotency:'PASS'
  };
}
async function main(){
  if(!['status','plan','provision','run','auto'].includes(command))
    fail('Usage: node scripts/qa-api.mjs status|plan|provision|run|auto [--confirm ...]');
  // Require explicit approval before even attaching to a tenant page.
  if(command==='provision'&&confirm!=='CREATE_ISOLATED_QA_APPS')
    fail('Provisioning requires --confirm CREATE_ISOLATED_QA_APPS');
  if(command==='run'&&confirm!=='RUN_ISOLATED_QA_ONLY')
    fail('Integration tests require --confirm RUN_ISOLATED_QA_ONLY');
  if(command==='auto'&&confirm!=='CREATE_AND_TEST_ISOLATED_QA')
    fail('One-command isolated QA requires --confirm CREATE_AND_TEST_ISOLATED_QA');
  const state=await loadState();
  if(command==='plan'){
    output({mode:'dry-run',origin:QA_ORIGIN,qaProfile:'visible isolated Edge',
      status:state?.phase||'not provisioned',existingApps:state?.apps||null,
      createOnly:['source','destination','management'],fieldsByApp:Object.fromEntries(roles.map(r=>[r,Object.keys(testFields[r])])),
      safety:'no API writes from plan; provision/run require explicit command confirmation and strict app-name checks'});
    return;
  }
  if(QA_ORIGIN==='https://qa-example.cybozu.com')fail('Set the private QA config file before accessing kintone');
  let session;
  try{
    session=await connectQA();
    if(command==='status'){
      output({mode:'read-only',...(await session.sessionStatus(QA_APP_PROBE)),provisioned:state?.phase==='ready',
        apps:state?.apps||null,profile:'ResoArcKintoneQA'});
    }else if(command==='provision')output(await prepare(session));
    else if(command==='auto'){
      const current=await loadState();
      if(!current)await prepare(session,'CREATE_ISOLATED_QA_APPS');
      output(await run(session,'RUN_ISOLATED_QA_ONLY'));
    }else output(await run(session));
  }finally{session?.close();}
}
export {testFields,loadState,saveState,assertIsolated,prepare,seed,run};
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  main().catch(error=>{
    console.error('ResoArc QA: '+error.message);
    process.exitCode=1;
  });
}
