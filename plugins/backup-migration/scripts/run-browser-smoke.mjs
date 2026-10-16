// Portable local-browser smoke launcher for Windows Edge and CI Chrome.
// Creates a disposable isolated profile; never reads personal browser cookies.
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {spawn, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const exists=async filename=>{
  if(!filename)return false;
  try{await fs.access(filename);return true;}catch{return false;}
};
const candidates=[
  process.env.RESOARC_BROWSER_EXECUTABLE,
  ...(process.platform==='win32'?[
    path.join(process.env['PROGRAMFILES(X86)']||'C:\\Program Files (x86)','Microsoft','Edge','Application','msedge.exe'),
    path.join(process.env.PROGRAMFILES||'C:\\Program Files','Microsoft','Edge','Application','msedge.exe'),
    path.join(process.env.LOCALAPPDATA||'','Microsoft','Edge','Application','msedge.exe')
  ]:[
    '/usr/bin/google-chrome','/usr/bin/google-chrome-stable',
    '/usr/bin/chromium','/usr/bin/chromium-browser',
    '/opt/google/chrome/chrome'
  ])
];
let executable;
for(const candidate of candidates)if(await exists(candidate)){executable=candidate;break;}
if(!executable)throw Error('Browser not found. Set RESOARC_BROWSER_EXECUTABLE to Chrome/Edge.');
const profile=await fs.mkdtemp(path.join(os.tmpdir(),'resoarc-backup-browser-'));
let browser=null,smoke=null;
try{
  const args=[
    '--headless=new','--disable-extensions','--disable-background-networking',
    '--no-first-run','--no-default-browser-check','--disable-gpu',
    '--remote-debugging-address=127.0.0.1','--remote-debugging-port=0',
    '--user-data-dir='+profile,'about:blank'
  ];
  if(process.platform==='linux')args.unshift('--no-sandbox');
  browser=spawn(executable,args,{stdio:'ignore',windowsHide:true});
  const portFile=path.join(profile,'DevToolsActivePort');
  let ready=false;
  for(let tries=0;tries<120;tries++){
    if(await exists(portFile)){ready=true;break;}
    if(browser.exitCode!==null)break;
    await new Promise(r=>setTimeout(r,125));
  }
  assert.ok(ready,'Isolated browser did not expose a CDP port');
  const smokePath=fileURLToPath(new URL('./browser-smoke.mjs',import.meta.url));
  const exitCode=await new Promise((resolve,reject)=>{
    smoke=spawn(process.execPath,[smokePath],{
      env:{...process.env,RESOARC_CDP_PROFILE:profile},
      cwd:path.dirname(smokePath),stdio:'inherit',windowsHide:true
    });
    const timeout=setTimeout(()=>{
      smoke.kill();reject(Error('Browser smoke test exceeded 60 seconds'));
    },60000);
    smoke.on('error',error=>{clearTimeout(timeout);reject(error);});
    smoke.on('exit',(code,signal)=>{clearTimeout(timeout);resolve({code,signal});});
  });
  assert.equal(exitCode.code,0,'Browser smoke returned nonzero exit status');
  console.log('BROWSER_CI_SMOKE_PASS');
}finally{
  if(smoke?.exitCode===null)smoke.kill();
  if(browser?.pid){
    if(process.platform==='win32')
      spawnSync('taskkill',['/PID',String(browser.pid),'/T','/F'],{stdio:'ignore',timeout:8000,windowsHide:true});
    else browser.kill('SIGTERM');
  }
  try{await fs.rm(profile,{recursive:true,force:true,maxRetries:8,retryDelay:350});}
  catch(error){console.warn('Temporary browser profile cleanup warning: '+error.message);}
}
