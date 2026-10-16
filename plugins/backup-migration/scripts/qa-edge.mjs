// ResoArc kintone QA: isolated *visible* Edge, independent of the headless browser.
// Run: node scripts/qa-edge.mjs start|status|open
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {QA_ORIGIN} from './qa-session.mjs';
const origin=QA_ORIGIN;
if(origin==='https://qa-example.cybozu.com')throw Error('Set your private Documents/MoleRemote/ResoArcKintoneQA-config.json first');
const tenant=new URL(origin);
if(tenant.protocol!=='https:'||!tenant.hostname.endsWith('.cybozu.com')||tenant.pathname!=='/'||tenant.search||tenant.hash||tenant.username||tenant.password)
  throw Error('Invalid RESOARC_KINTONE_ORIGIN');
const profile=path.join(os.homedir(),'Documents','MoleRemote','ResoArcKintoneQA');
const portFile=path.join(profile,'DevToolsActivePort');
async function browser(){
  try{
    const port=Number((await fs.readFile(portFile,'utf8')).split(/\r?\n/)[0]);
    if(!Number.isSafeInteger(port)||port<1024||port>65535)return null;
    const res=await fetch('http://127.0.0.1:'+port+'/json/version',{signal:AbortSignal.timeout(1500)});
    if(!res.ok)return null;
    const value=await res.json();
    if(!/^Edg\//.test(value.Browser||''))return null;
    return {port,version:value.Browser};
  }catch{return null;}
}
const cmd=process.argv[2]||'start';
if(cmd==='status'){
  const connected=await browser();
  console.log(JSON.stringify({running:!!connected,profile,origin, ...(connected||{})}));
}else if(cmd==='start'||cmd==='open'){
  let connected=await browser();
  if(!connected){
    if(cmd==='open')throw Error('Edge is not running. Start it first.');
    const candidates=[
      path.join(process.env['PROGRAMFILES(X86)']||'C:\\Program Files (x86)','Microsoft','Edge','Application','msedge.exe'),
      path.join(process.env.PROGRAMFILES||'C:\\Program Files','Microsoft','Edge','Application','msedge.exe')
    ];
    let exe;
    for(const p of candidates){try{await fs.access(p);exe=p;break;}catch{}}
    if(!exe)throw Error('Microsoft Edge is not installed');
    await fs.mkdir(profile,{recursive:true});
    const args=['--remote-debugging-address=127.0.0.1','--remote-debugging-port=0',
      '--disable-extensions','--no-first-run','--no-default-browser-check',
      '--user-data-dir='+profile,'--new-window',origin+'/k/'];
    const child=spawn(exe,args,{detached:true,windowsHide:false,stdio:'ignore'});
    child.on('error',()=>{});
    child.unref();
    for(let i=0;i<70;i++){
      await new Promise(r=>setTimeout(r,200));
      connected=await browser();if(connected)break;
    }
    if(!connected)throw Error('Visible Edge did not expose CDP; the GUI session may be disconnected');
  }
  console.log(JSON.stringify({ok:true,mode:'visible isolated Edge',origin,profile,port:connected.port,message:'Use this Edge window to log in to kintone.'}));
}else throw Error('Usage: node scripts/qa-edge.mjs start|status|open');
