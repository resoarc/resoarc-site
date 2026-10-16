// Minimal, localhost-only CDP transport to a visible, isolated Edge profile.
// Authentication stays inside Edge; no cookies or tokens leave the browser.
import fs from 'node:fs/promises';
import {readFileSync,existsSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// The actual tenant URL is never committed to the public repository.
// Use the local-only Documents/MoleRemote/ResoArcKintoneQA-config.json file.
export const QA_SETTINGS_PATH=path.join(os.homedir(),'Documents','MoleRemote','ResoArcKintoneQA-config.json');
const settings=existsSync(QA_SETTINGS_PATH)?JSON.parse(readFileSync(QA_SETTINGS_PATH,'utf8')):{};
export const QA_ORIGIN=process.env.RESOARC_KINTONE_ORIGIN||settings.origin||'https://qa-example.cybozu.com';
export const QA_APP_PROBE=Number(process.env.RESOARC_QA_PROBE_APP||settings.probeAppId||1);
export const QA_PROFILE=path.join(os.homedir(),'Documents','MoleRemote','ResoArcKintoneQA');
export const QA_STATE=process.env.RESOARC_QA_STATE || path.join(os.homedir(),'Documents','MoleRemote','ResoArcKintoneQA-state.json');

export function checkedOrigin(origin=QA_ORIGIN){
  const url=new URL(origin), expected=new URL(QA_ORIGIN);
  const valid=u=>u.protocol==='https:'&&u.hostname.endsWith('.cybozu.com')&&
    u.pathname==='/'&&!u.search&&!u.hash&&!u.username&&!u.password;
  if(!valid(url)||!valid(expected)||url.origin!==expected.origin)
    throw Error('This QA harness is restricted to the configured developer tenant');
  return url.origin;
}
checkedOrigin();
if(!Number.isSafeInteger(QA_APP_PROBE)||QA_APP_PROBE<1)
  throw Error('Invalid local QA app probe ID');

async function devtoolsPort(profile=QA_PROFILE){
  const raw=await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8');
  const port=Number(raw.split(/\r?\n/)[0]);
  if(!Number.isSafeInteger(port)||port<1024||port>65535)throw Error('Invalid QA Edge port');
  const response=await fetch('http://127.0.0.1:'+port+'/json/version',{signal:AbortSignal.timeout(4000)});
  if(!response.ok)throw Error('QA Edge CDP is not available');
  const version=await response.json();
  if(!/^Edg\//.test(version.Browser||''))throw Error('QA Edge is not Microsoft Edge');
  return port;
}

export async function connectQA({profile=QA_PROFILE,origin=QA_ORIGIN}={}){
  checkedOrigin(origin);
  const port=await devtoolsPort(profile);
  const response=await fetch('http://127.0.0.1:'+port+'/json/list',{signal:AbortSignal.timeout(4000)});
  const tabs=await response.json();
  const match=t=>{
    if(t.type!=='page')return false;
    try{
      const url=new URL(t.url);
      return url.origin===origin;
    }catch{return false;}
  };
  const pages=tabs.filter(match);
  const tab=pages.find(t=>!new URL(t.url).pathname.startsWith('/login'))||pages[0];
  if(!tab)throw Error('Open the kintone developer tenant in the visible QA Edge before testing');
  const ws=new WebSocket(tab.webSocketDebuggerUrl);
  const pending=new Map();
  let nextId=0, closed=false;
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('QA Edge websocket connection timed out')),8000);
    ws.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
    ws.addEventListener('error',()=>{clearTimeout(timer);reject(Error('QA Edge websocket connection failed'));},{once:true});
  });
  ws.addEventListener('message',event=>{
    let response;
    try{response=JSON.parse(event.data);}catch{return;}
    const entry=pending.get(response.id);
    if(!entry)return;
    clearTimeout(entry.timer);pending.delete(response.id);
    if(response.error)entry.reject(Error('QA browser evaluation error'));
    else entry.resolve(response.result);
  });
  const send=(method,params={})=>{
    if(closed)throw Error('CDP session is closed');
    return new Promise((resolve,reject)=>{
      const id=++nextId;
      const timer=setTimeout(()=>{pending.delete(id);reject(Error('QA Edge request timed out'));},45000);
      pending.set(id,{resolve,reject,timer});
      ws.send(JSON.stringify({id,method,params}));
    });
  };
  async function evaluate(fn,args=[]){
    const expression='('+fn.toString()+')('+args.map(a=>JSON.stringify(a)).join(',')+')';
    const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(result.exceptionDetails){
      const description=String(result.exceptionDetails.exception?.description||'').split('\n')[0];
      throw Error('QA browser script error: '+description.slice(0,170));
    }
    if(!result.result || !Object.hasOwn(result.result,'value'))throw Error('QA browser returned no value');
    return result.result.value;
  }
  async function request(endpoint,method='GET',body={}){
    if(!/^\/k\/v1\/[A-Za-z0-9/.-]+\.json$/.test(endpoint)||!['GET','POST'].includes(method))
      throw Error('Only expected kintone REST API paths and GET/POST methods are supported');
    const data=await evaluate(async(path,httpMethod,params,expectedOrigin)=>{
      if(location.origin!==expectedOrigin)throw Error('Wrong tenant tab origin');
      if(!window.kintone?.api)throw Error('Log in on a kintone page before API testing');
      try{
        const result=await kintone.api(kintone.api.url(path,true),httpMethod,params);
        return {ok:true,result};
      }catch(error){
        return {ok:false,errorCode:String(error?.code||'UNKNOWN'),status:Number(error?.status||0)};
      }
    },[endpoint,method,body,origin]);
    if(!data?.ok)throw Error('kintone API '+method+' '+endpoint+' rejected: '+data?.errorCode+' HTTP '+data?.status);
    return data.result;
  }
  async function upload(bytes,filename,type='text/plain'){
    if(!(bytes instanceof Uint8Array)||bytes.byteLength>2000000)throw Error('Test attachments must be <=2MB');
    const result=await evaluate(async(data,name,mime,expectedOrigin)=>{
      if(location.origin!==expectedOrigin||!window.kintone?.getRequestToken)throw Error('Not an authorized kintone page');
      const binary=Uint8Array.from(atob(data),c=>c.charCodeAt(0));
      const form=new FormData();
      form.append('__REQUEST_TOKEN__',kintone.getRequestToken());
      form.append('file',new Blob([binary],{type:mime}),name);
      const response=await fetch('/k/v1/file.json',{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest'},body:form});
      if(!response.ok)return {ok:false,status:response.status};
      const body=await response.json();
      return {ok:typeof body.fileKey==='string',fileKey:body.fileKey};
    },[Buffer.from(bytes).toString('base64'),filename,type,origin]);
    if(!result?.ok)throw Error('kintone test file upload failed HTTP '+result?.status);
    return result.fileKey;
  }
  async function download(fileKey){
    if(typeof fileKey!=='string'||!fileKey||fileKey.length>512)throw Error('Bad file key');
    const result=await evaluate(async(key,expectedOrigin)=>{
      if(location.origin!==expectedOrigin)throw Error('Wrong origin');
      const response=await fetch('/k/v1/file.json?fileKey='+encodeURIComponent(key),{
        method:'GET',headers:{'X-Requested-With':'XMLHttpRequest'}
      });
      if(!response.ok)return {ok:false,status:response.status};
      const buffer=new Uint8Array(await response.arrayBuffer());
      if(buffer.byteLength>2000000)return {ok:false,status:'TOO_LARGE'};
      let binary='';
      for(let i=0;i<buffer.length;i++)binary+=String.fromCharCode(buffer[i]);
      return {ok:true,data:btoa(binary)};
    },[fileKey,origin]);
    if(!result?.ok)throw Error('kintone test file download failed '+result?.status);
    return new Uint8Array(Buffer.from(result.data,'base64'));
  }
  async function sessionStatus(app=49){
    return evaluate(async(id,expectedOrigin)=>{
      if(location.origin!==expectedOrigin)return {authenticated:false,reason:'WRONG_ORIGIN'};
      const get=async pathname=>{
        try{
          const response=await fetch(pathname,{credentials:'same-origin',cache:'no-store',
            headers:{'X-Requested-With':'XMLHttpRequest'}});
          return response.status;
        }catch{return 0;}
      };
      const appHttp=await get('/k/v1/app.json?id='+id);
      const fieldsHttp=await get('/k/v1/app/form/fields.json?app='+id);
      let signedIn=false;
      try{signedIn=!!window.kintone?.getLoginUser?.()?.code;}catch{}
      return {authenticated:signedIn&&appHttp!==401&&fieldsHttp!==401,
        appReadable:appHttp===200&&fieldsHttp===200,
        appHttp,fieldsHttp,origin:location.origin};
    },[app,origin]);
  }
  return {
    tabId:tab.id,origin,request,upload,download,sessionStatus,evaluate,
    close(){
      closed=true;
      for(const pendingEntry of pending.values()){clearTimeout(pendingEntry.timer);pendingEntry.reject(Error('QA Edge disconnected'));}
      pending.clear();
      try{ws.close();}catch{}
    }
  };
}
