/* ResoArc Clock: fail-closed Cloudflare credential preflight.
 * Never reads token values or prints Wrangler account identity.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const root=path.resolve(__dirname,'..','worker');
const CONFIG='wrangler.clock.local.jsonc';
function safeConfig(c){
 if(!c||typeof c!=='object')return false;
 const v=c.vars||{};
 return c.name==='resoarc-clock-self-hosted'&&v.RA_CLOCK_ENABLED==='true'&&
   v.RA_ALLOW_WRITES==='false'&&v.RA_POLL_MODE==='adaptive'&&
   /^[1-9]\d*$/.test(String(v.RA_CONTROL_APP_ID||''))&&
   c.workers_dev===false&&c.preview_urls===false&&
   Array.isArray(c.kv_namespaces)&&c.kv_namespaces.length===1&&
   c.kv_namespaces[0].binding==='RA_CLOCK_STATE'&&
   Array.isArray(c.triggers?.crons)&&c.triggers.crons.length===1&&c.triggers.crons[0]==='* * * * *';
}
function checkAuth(run=cp.spawnSync){
 const result=run('cmd.exe',['/d','/s','/c','npx.cmd wrangler whoami --config '+CONFIG],
 {cwd:root,windowsHide:true,encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:30000,maxBuffer:204800});
 return result.status===0&&!result.error;
}
function checkWorkerAccess(run=cp.spawnSync){
 const result=run('cmd.exe',['/d','/s','/c','npx.cmd wrangler deployments list --config '+CONFIG+' --json'],
 {cwd:root,windowsHide:true,encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:30000,maxBuffer:2097152});
 if(result.status!==0||result.error)return false;
 try{return Array.isArray(JSON.parse(result.stdout||''));}
 catch{return false;}
}
function preflight(run){
 let safe=false;
 try{safe=safeConfig(JSON.parse(fs.readFileSync(path.join(root,CONFIG),'utf8').replace(/^\uFEFF/,'')));}
 catch{return {safeClockConfig:false,cloudflareAuthenticated:false,ready:false};}
 if(!safe)return {safeClockConfig:false,cloudflareAuthenticated:false,ready:false};
 const auth=checkAuth(run);
 const access=auth&&checkWorkerAccess(run);
 return {safeClockConfig:true,cloudflareAuthenticated:auth,cloudflareTargetAccessible:access,ready:auth&&access};
}
if(require.main===module){
 const result=preflight();
 console.log(JSON.stringify(result));
 if(!result.ready)process.exitCode=2;
}
module.exports={safeConfig,checkAuth,checkWorkerAccess,preflight};
