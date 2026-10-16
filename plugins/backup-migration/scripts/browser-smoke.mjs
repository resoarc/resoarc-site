// Automated browser integration smoke test, using ONLY an isolated local mock.
// Runs in MoleRemote BrowserCDP Edge: no tenant credentials, no external writes.
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';

const base=process.env.RESOARC_CDP_PROFILE || path.join(os.homedir(),'Documents','MoleRemote','BrowserCDP');
const devtools=await fs.readFile(path.join(base,'DevToolsActivePort'),'utf8');
const port=Number(devtools.split(/\r?\n/)[0]);
assert.ok(Number.isInteger(port)&&port>0);
const bundle=await fs.readFile(new URL('../dist/resoarc-backup.js',import.meta.url));
const html=String.raw`<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>ResoArc browser smoke</title></head>
<body><main id="header"></main>
<script>
(()=> {
 const src={properties:{
   Title:{type:'SINGLE_LINE_TEXT',code:'Title',label:'題名'},
   Amount:{type:'NUMBER',code:'Amount',label:'数値'},
   Notes:{type:'SUBTABLE',code:'Notes',label:'備考',fields:{Memo:{type:'MULTI_LINE_TEXT',code:'Memo',label:'メモ'}}}
 }};
 const dest={properties:{...src.properties,ResoArcRestoreKey:{type:'SINGLE_LINE_TEXT',unique:true,code:'ResoArcRestoreKey'}}};
 const rows=Array.from({length:501},(_,i)=>({
   Title:{value:'Sample '+i},Amount:{value:String(i)},
   Notes:{value:[{value:{Memo:{value:'line '+i}}}]}
 }));
 const h=window.__test={calls:[],target:[],answers:[],cursors:new Map(),number:0,zip:null,ready:false,destinationFields:dest,draftApp:null,draftFields:null};
 window.prompt=()=>h.answers.shift()??'';
 window.confirm=()=>true;
 const api=async(url,method,args)=>{
   h.calls.push({url,method});
   if(url==='/k/v1/app/form/fields.json' && method==='GET')return args.app===42?src:h.destinationFields;
   if(url==='/k/v1/app/form/layout.json' && method==='GET')return {layout:[]};
   if(url==='/k/v1/preview/app.json' && method==='POST'){
     h.draftApp={id:77,name:args.name};
     return {app:'77'};
   }
   if(url==='/k/v1/preview/app/form/fields.json' && method==='POST'){
     if(args.app!==77)throw Error('draft app ID mismatch');
     h.draftFields=structuredClone(args.properties);
     return {revision:'2'};
   }
   if(url==='/k/v1/records/cursor.json' && method==='POST'){
     const id=String(++h.number);
     h.cursors.set(id,{rows:[...(args.app===42?rows:h.target)],index:0,size:args.size});
     return {id};
   }
   if(url==='/k/v1/records/cursor.json' && method==='GET'){
     const c=h.cursors.get(args.id);
     if(!c)throw Error('unknown cursor');
     const result=c.rows.slice(c.index,c.index+c.size);
     c.index+=c.size;
     const next=c.index<c.rows.length;
     if(!next)h.cursors.delete(args.id);
     return {records:result,next};
   }
   if(url==='/k/v1/records/cursor.json' && method==='DELETE'){h.cursors.delete(args.id);return {};}
   if(url==='/k/v1/record.json' && method==='POST')return {id:'1'};
   if(url==='/k/v1/record.json' && method==='GET')return {record:{
     SourceAppId:{value:'42'},ArchiveHash:{value:h.hash},
     Archive:{value:[{fileKey:'fake-zip',size:String(h.zip.byteLength)}]}
   }};
   if(url==='/k/v1/records.json' && method==='POST'){
     if(args.app!==55)throw Error('destination app mismatch');
     const before=new Set(h.target.map(r=>r.ResoArcRestoreKey.value));
     for(const r of args.records) {
       if(before.has(r.ResoArcRestoreKey.value))throw Error('duplicate restore');
       before.add(r.ResoArcRestoreKey.value);
     }
     h.target.push(...args.records);
     return {ids:args.records.map((_,i)=>String(h.target.length-args.records.length+i+1))};
   }
   throw Error('Unexpected kintone API '+url+' '+method);
 };
 api.url=p=>p;
 window.kintone={
   api,app:{getId:()=>99,getHeaderMenuSpaceElement:()=>document.getElementById('header')},
   getRequestToken:()=> 'mock-only-request-token',
   events:{on:(_,fn)=>setTimeout(()=>{fn({type:'app.record.index.show'});h.ready=true},0)}
 };
 const fetchOrig=window.fetch.bind(window);
 window.fetch=async(url,opts={})=>{
   const u=String(url);
   if(u.startsWith('/k/v1/file.json')){
     if(opts.method==='POST'){
       const blob=opts.body.get('file');
       h.zip=new Uint8Array(await blob.arrayBuffer());
       const digest=await crypto.subtle.digest('SHA-256',h.zip);
       h.hash=Array.from(new Uint8Array(digest)).map(n=>n.toString(16).padStart(2,'0')).join('');
       return new Response(JSON.stringify({fileKey:'fake-zip'}),{status:200,headers:{'Content-Type':'application/json'}});
     }
     return new Response(h.zip,{status:200});
   }
   return fetchOrig(url,opts);
 };
})();
</script><script src="/bundle.js"></script></body></html>`;
const server=http.createServer((req,res)=>{
  if(req.url==='/bundle.js'){res.writeHead(200,{'Content-Type':'application/javascript;charset=utf-8'});res.end(bundle);return;}
  res.writeHead(200,{'Content-Type':'text/html;charset=utf-8'});res.end(html);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const address='http://127.0.0.1:'+server.address().port+'/';
let target, socket, pending=new Map(),seq=0;
const dev='http://127.0.0.1:'+port;
try{
  target=await (await fetch(dev+'/json/new?'+encodeURIComponent(address),{method:'PUT'})).json();
  socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{
    socket.addEventListener('open',resolve,{once:true});
    socket.addEventListener('error',reject,{once:true});
    setTimeout(()=>reject(Error('WebSocket timeout')),8000);
  });
  socket.addEventListener('message',event=>{
    const message=JSON.parse(event.data), entry=pending.get(message.id);
    if(!entry)return;clearTimeout(entry.timer);pending.delete(message.id);
    if(message.error)entry.reject(Error(message.error.message));else entry.resolve(message.result);
  });
  const send=(method,params)=>new Promise((resolve,reject)=>{
    const id=++seq, timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout'));},30000);
    pending.set(id,{resolve,reject,timer});
    socket.send(JSON.stringify({id,method,params}));
  });
  const evaluate=async expression=>{
    const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(result.exceptionDetails)throw Error('JS exception '+JSON.stringify(result.exceptionDetails).slice(0,400));
    return result.result.value;
  };
  const wait=async(expression,timeout=18000)=>{
    const until=Date.now()+timeout;
    while(Date.now()<until){
      const result=await evaluate(expression);
      if(result)return result;
      await new Promise(r=>setTimeout(r,120));
    }
    throw Error('Browser condition timeout: '+expression);
  };
  await wait("window.__test?.ready && document.querySelector('[data-resoarc-backup]')?.querySelectorAll('button').length >= 7");
  await evaluate("window.__test.answers=['42','BrowserCDP smoke']; [...document.querySelectorAll('button')].find(b=>b.textContent==='バックアップを作成').click(); true");
  const backup=await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('バックアップ作成完了') && {text:document.querySelector('[data-resoarc-backup]').innerText,files:window.__test.zip?.length,hash:window.__test.hash}",25000);
  assert.match(backup.text,/501 件/);
  assert.ok(backup.files>100);

  // Browser-level safety checks must finish before any destination writes.
  // 1. A changed ZIP with its original management-record hash is rejected.
  await evaluate("window.__test.originalZip=window.__test.zip.slice(); window.__test.zip[25]^=1; window.__test.answers=['1','55','']; [...document.querySelectorAll('button')].find(b=>b.textContent==='復元プレビュー').click(); true");
  await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('ZIP全体のSHA-256が一致しません') && true",20000);
  assert.equal(await evaluate("window.__test.target.length"),0,'modified ZIP must never write a record');
  await evaluate("window.__test.zip=window.__test.originalZip; true");

  // 2. Missing unique marker on the destination must reject a restore.
  await evaluate("window.__test.destinationFields.properties.ResoArcRestoreKey.unique=false; window.__test.answers=['1','55','']; [...document.querySelectorAll('button')].find(b=>b.textContent==='復元プレビュー').click(); true");
  await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('重複禁止の文字列') && true",20000);
  assert.equal(await evaluate("window.__test.target.length"),0,'missing unique marker must never write a record');
  await evaluate("window.__test.destinationFields.properties.ResoArcRestoreKey.unique=true; true");

  // 3. Confirmation must refuse any input that differs from the exact phrase.
  await evaluate("window.__test.answers=['1','55','']; [...document.querySelectorAll('button')].find(b=>b.textContent==='復元プレビュー').click(); true");
  const preview=await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('新規追加予定: 501 件') && true",20000);
  assert.equal(preview,true);
  await evaluate("window.__test.answers=['INVALID CONFIRMATION']; [...document.querySelectorAll('button')].find(b=>b.textContent==='復元を実行 (追記のみ)').click(); true");
  assert.equal(await evaluate("window.__test.target.length"),0,'wrong confirmation phrase must never write a record');
  await evaluate("window.__test.answers=['RESTORE 55 501']; [...document.querySelectorAll('button')].find(b=>b.textContent==='復元を実行 (追記のみ)').click(); true");
  const restored=await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('復元処理完了') && {total:window.__test.target.length,last:window.__test.target.at(-1)?.Notes.value[0].value.Memo.value,post:window.__test.calls.filter(c=>c.url==='/k/v1/records.json'&&c.method==='POST').length}",30000);
  assert.equal(restored.total,501);
  assert.equal(restored.last,'line 500');
  assert.equal(restored.post,26);
  await evaluate("window.__test.answers=['1','55','']; [...document.querySelectorAll('button')].find(b=>b.textContent==='復元プレビュー').click(); true");
  await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('新規追加予定: 0 件') && true",15000);

  // 4. New app creation is draft-only: only preview endpoints may be used.
  await evaluate("window.__test.answers=['1','ResoArc Draft UI']; [...document.querySelectorAll('button')].find(b=>b.textContent==='管理レコードから新規アプリ構造プレビュー').click(); true");
  await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('新規アプリ構造のプレビュー') && true",20000);
  await evaluate("window.__test.answers=['CREATE ResoArc Draft UI']; [...document.querySelectorAll('button')].find(b=>b.textContent==='新規アプリの下書きを作成 (データは書かない)').click(); true");
  const draft=await wait("document.querySelector('[data-resoarc-backup]')?.innerText.includes('新規アプリ #77 の下書きを作成しました') && {app:window.__test.draftApp,fields:window.__test.draftFields && Object.keys(window.__test.draftFields).length,unique:window.__test.draftFields?.ResoArcRestoreKey?.unique,records:window.__test.target.length,deploymentCalls:window.__test.calls.filter(c=>c.url.includes('deploy')).length}",20000);
  assert.equal(draft.app.name,'ResoArc Draft UI');
  assert.ok(draft.fields>=4);
  assert.equal(draft.unique,true);
  assert.equal(draft.records,501,'draft creation must never alter the restored rows');
  assert.equal(draft.deploymentCalls,0,'draft creation must not deploy the app');

  console.log(JSON.stringify({ok:true,scenario:'headless Edge actual UI script, mocked same-origin kintone API',recordCount:restored.total,restoreBatches:restored.post,zipBytes:backup.files,resumePending:0,rejectedWithoutWrites:['tampered-zip','missing-unique-marker','wrong-confirmation'],newAppDraftId:draft.app.id,deployCalls:0,credentialsUsed:false}));
}finally{
  try{socket?.close();}catch{}
  if(target?.id)try{await fetch(dev+'/json/close/'+target.id);}catch{}
  server.closeAllConnections();
  await new Promise(r=>server.close(r));
}
