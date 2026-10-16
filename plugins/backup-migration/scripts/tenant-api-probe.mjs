// Read-only authenticated API readiness probe for ResoArc Backup & Migration.
// Use with an already-open kintone tab in Mole Remote's isolated BrowserCDP Edge.
// Never reads, exports, or stores passwords, cookies, request tokens or response bodies.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';

function requiredArg(flag) {
  const position=process.argv.indexOf(flag);
  if(position<0||!process.argv[position+1])
    throw Error('Usage: node scripts/tenant-api-probe.mjs --origin https://TENANT.cybozu.com --app 123');
  return process.argv[position+1];
}
const candidate=new URL(requiredArg('--origin'));
if(candidate.protocol!=='https:'||!candidate.hostname.endsWith('.cybozu.com')||
   candidate.username||candidate.password||candidate.search||candidate.hash||candidate.pathname!=='/')
  throw Error('Specify an HTTPS cybozu tenant origin, without a path or credentials');
const origin=candidate.origin;
const app=Number(requiredArg('--app'));
if(!Number.isSafeInteger(app)||app<1)throw Error('Positive kintone app ID required');
const profile=process.env.RESOARC_CDP_PROFILE ||
 path.join(os.homedir(),'Documents','MoleRemote','BrowserCDP');
const portFile=await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8');
const port=Number(portFile.split(/\r?\n/)[0]);
if(!Number.isSafeInteger(port)||port<1024||port>65535)
  throw Error('Isolated Edge CDP port is unavailable');
const devtools='http://127.0.0.1:'+port;
const tabs=await (await fetch(devtools+'/json/list',{signal:AbortSignal.timeout(5000)})).json();
const candidates=tabs.filter(t=>{
  try{return t.type==='page'&&new URL(t.url).origin===origin;}catch{return false;}
});
const tab=candidates.find(t=>!/^\/login(?:\/|$)/.test(new URL(t.url).pathname)) || candidates[0];
if(!tab)throw Error('No tenant tab in isolated Edge. Open it with browser_headless_open first.');
const ws=new WebSocket(tab.webSocketDebuggerUrl);
let requestId=0;
const pending=new Map();
async function checkTenantPage(expectedOrigin,appId){
  if(location.origin!==expectedOrigin)return {ready:false,error:'Wrong origin'};
  const check=async endpoint=>{
    try{
      const response=await fetch(endpoint,{
        method:'GET',credentials:'same-origin',cache:'no-store',
        headers:{'X-Requested-With':'XMLHttpRequest'}
      });
      return {
        status:response.status,redirected:response.redirected,
        json:(response.headers.get('content-type')||'').toLowerCase().includes('json')
      };
    }catch{return {status:0,redirected:false,json:false};}
  };
  const appResult=await check('/k/v1/app.json?id='+appId);
  const fieldsResult=await check('/k/v1/app/form/fields.json?app='+appId);
  return {
    tenantHost:location.hostname,
    loginPage:/^\/login(?:\/|$)/.test(location.pathname),
    appRead:appResult,fieldsRead:fieldsResult,
    ready:appResult.status===200&&appResult.json&&!appResult.redirected &&
          fieldsResult.status===200&&fieldsResult.json&&!fieldsResult.redirected
  };
}
try {
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('CDP connection timeout')),7000);
    ws.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
    ws.addEventListener('error',()=>{clearTimeout(timer);reject(Error('CDP connection failed'));},{once:true});
  });
  ws.addEventListener('message',event=>{
    let msg;try{msg=JSON.parse(event.data);}catch{return;}
    const entry=pending.get(msg.id);if(!entry)return;
    clearTimeout(entry.timer);pending.delete(msg.id);
    if(msg.error)entry.reject(Error('CDP evaluation failed'));else entry.resolve(msg.result);
  });
  const send=(method,params)=>new Promise((resolve,reject)=>{
    const id=++requestId;
    const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timed out'));},15000);
    pending.set(id,{resolve,reject,timer});
    ws.send(JSON.stringify({id,method,params}));
  });
  const expression='('+checkTenantPage.toString()+')('+JSON.stringify(origin)+','+app+')';
  const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(result.exceptionDetails||!result.result?.value)
    throw Error('Tenant API readiness check failed without exposing response data');
  console.log(JSON.stringify({probe:'ResoArc read-only kintone tenant API',...result.result.value}));
}finally{
  for(const [id,p] of pending){clearTimeout(p.timer);pending.delete(id);p.reject(Error('CDP disconnected'));}
  ws.close();
}
