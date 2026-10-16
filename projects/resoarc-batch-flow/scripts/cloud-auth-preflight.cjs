/* ResoArc Clock: fail-closed Cloudflare credential and *deployed state* preflight.
 * Never reads or prints token values, tenant names, account identifiers, or raw Cloudflare responses.
 */
'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const root=path.resolve(__dirname,'..','worker');
const CONFIG='wrangler.clock.local.jsonc';
const SAFE_VERSION_ID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function safeConfig(c){
 if(!c||typeof c!=='object')return false;
 const v=c.vars||{};
 return c.name==='resoarc-clock-self-hosted'&&v.RA_CLOCK_ENABLED==='true'&&
   v.RA_ALLOW_WRITES==='false'&&v.RA_POLL_MODE==='adaptive'&&
   !['RA_E2E_ONLY_BATCH_ID','RA_E2E_ALLOWED_APP_ID','RA_ALLOW_UNSCOPED_WRITES'].some(k=>k in v)&&
   /^[1-9]\d*$/.test(String(v.RA_CONTROL_APP_ID||''))&&
   c.workers_dev===false&&c.preview_urls===false&&
   Array.isArray(c.kv_namespaces)&&c.kv_namespaces.length===1&&
   c.kv_namespaces[0].binding==='RA_CLOCK_STATE'&&
   Array.isArray(c.triggers?.crons)&&c.triggers.crons.length===1&&c.triggers.crons[0]==='* * * * *';
}
function invoke(args,run=cp.spawnSync){
 return run('cmd.exe',['/d','/s','/c','npx.cmd wrangler '+args],
   {cwd:root,windowsHide:true,encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:30000,maxBuffer:2097152});
}
function checkAuth(run=cp.spawnSync){
 const r=invoke('whoami --config '+CONFIG,run);
 return r.status===0&&!r.error;
}
function getDeployments(run=cp.spawnSync){
 const r=invoke('deployments list --config '+CONFIG+' --json',run);
 if(r.status!==0||r.error)return null;
 try{
   const value=JSON.parse(r.stdout||'');
   return Array.isArray(value)?value:null;
 }catch{return null;}
}
function checkWorkerAccess(run=cp.spawnSync){return getDeployments(run)!==null;}
function chooseDeployedVersion(deployments){
 if(!Array.isArray(deployments)||!deployments.length)return null;
 const sorted=deployments.filter(d=>typeof d.created_on==='string'&&Array.isArray(d.versions))
   .sort((a,b)=>Date.parse(b.created_on)-Date.parse(a.created_on));
 if(!sorted.length)return null;
 const versions=sorted[0].versions;
 // Do not approve canary or split traffic when verifying exact write-mode safety.
 if(versions.length!==1||versions[0].percentage!==100)return null;
 const id=versions[0].version_id;
 return typeof id==='string'&&SAFE_VERSION_ID.test(id)?id:null;
}
function verifyRemoteBindings(data,expected){
 const b=data?.resources?.bindings;
 if(!Array.isArray(b)||!safeConfig(expected))return false;
 const named=new Map();
 for(const v of b){
   if(typeof v?.name!=='string'||named.has(v.name))return false;
   named.set(v.name,v);
 }
 const eq=(name,val)=>named.get(name)?.type==='plain_text'&&named.get(name)?.text===val;
 return eq('RA_CONTROL_APP_ID',String(expected.vars.RA_CONTROL_APP_ID))&&
   eq('RA_CLOCK_ENABLED','true')&&
   eq('RA_ALLOW_WRITES','false')&&eq('RA_POLL_MODE','adaptive')&&
   named.get('RA_CLOCK_STATE')?.type==='kv_namespace'&&
   named.get('KINTONE_DOMAIN')?.type==='secret_text'&&
   named.get('KINTONE_API_TOKENS')?.type==='secret_text'&&
   !['RA_E2E_ONLY_BATCH_ID','RA_E2E_ALLOWED_APP_ID','RA_ALLOW_UNSCOPED_WRITES'].some(k=>named.has(k));
}
function checkDeployedSafety(config,run=cp.spawnSync){
 const deployments=getDeployments(run);
 const id=chooseDeployedVersion(deployments);
 if(!id)return {targetAccessible:deployments!==null,remoteReadOnlyVerified:false};
 const r=invoke('versions view '+id+' --config '+CONFIG+' --json',run);
 if(r.status!==0||r.error)return {targetAccessible:true,remoteReadOnlyVerified:false};
 let view;
 try{view=JSON.parse(r.stdout||'');}catch{return {targetAccessible:true,remoteReadOnlyVerified:false};}
 return {targetAccessible:true,remoteReadOnlyVerified:verifyRemoteBindings(view,config)};
}
function preflight(run=cp.spawnSync){
 let config=null;
 try{config=JSON.parse(fs.readFileSync(path.join(root,CONFIG),'utf8').replace(/^\uFEFF/,''));}
 catch{return {safeClockConfig:false,cloudflareAuthenticated:false,cloudflareTargetAccessible:false,remoteReadOnlyVerified:false,ready:false};}
 if(!safeConfig(config))return {safeClockConfig:false,cloudflareAuthenticated:false,cloudflareTargetAccessible:false,remoteReadOnlyVerified:false,ready:false};
 const auth=checkAuth(run);
 const remote=auth?checkDeployedSafety(config,run):{targetAccessible:false,remoteReadOnlyVerified:false};
 return {safeClockConfig:true,cloudflareAuthenticated:auth,
   cloudflareTargetAccessible:remote.targetAccessible,
   remoteReadOnlyVerified:remote.remoteReadOnlyVerified,
   ready:auth&&remote.targetAccessible&&remote.remoteReadOnlyVerified};
}
if(require.main===module){
 const result=preflight();
 console.log(JSON.stringify(result));
 if(!result.ready)process.exitCode=2;
}
module.exports={safeConfig,checkAuth,checkWorkerAccess,chooseDeployedVersion,verifyRemoteBindings,checkDeployedSafety,preflight};
