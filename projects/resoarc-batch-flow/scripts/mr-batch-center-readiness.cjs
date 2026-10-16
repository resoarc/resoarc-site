/* ResoArc Clock: read-only readiness using Mole Remote kintone fast-test tools. MIT */
'use strict';
const path=require('node:path');
const os=require('node:os');
const fs=require('node:fs');
const ROOT=path.resolve(__dirname,'..');
const MR_ROOT=process.env.MOLE_REMOTE_ROOT || path.join(os.homedir(),'mole-remote');
const PLUGIN_NAME='ResoArc Batch Center';
function schemaFields(schema){
  const properties=schema?.properties;
  if(!properties || typeof properties!=='object')throw Error('Control app field schema is unavailable');
  return {
    top:Object.keys(properties),
    table:Object.keys(properties.Steps?.fields||{})
  };
}
function evaluateSchema(available,expected){
  const missingFields=expected.top.filter(key=>!available?.[key]);
  const actualSubtable=available?.Steps?.fields || {};
  const missingTableFields=expected.table.filter(key=>!actualSubtable[key]);
  return {ok:missingFields.length===0&&missingTableFields.length===0,missingFields,missingTableFields};
}
function matchingApps(apps){
  return (Array.isArray(apps)?apps:[]).filter(a=>/resoarc.*(?:batch|clock|バッチ)|バッチ管理/i.test(String(a.name||'')))
    .map(a=>({appId:Number(a.appId||a.app),name:String(a.name||'').slice(0,80)}))
    .filter(a=>Number.isSafeInteger(a.appId)&&a.appId>0)
    .slice(0,30);
}
async function inspectCenter(browser,env,centerAppId){
  if(!(await browser.port()))return {status:'isolated_browser_unavailable',candidates:[]};
  let tab,session;
  try{
    tab=await browser.open(browser.loginUrl);
    session=await browser.connect(tab.id);
    let ready=false;
    for(let i=0;i<30;i++){
      const page=await session.evalJS('(()=>({loaded:document.readyState==="complete",loggedIn:!!window.kintone?.api}))()');
      if(page?.loaded&&page?.loggedIn){ready=true;break;}
      await new Promise(resolve=>setTimeout(resolve,250));
    }
    if(!ready)return {status:'authentication_required',candidates:[]};
    const discovered=await session.evalJS(`(async()=>{try{
      const r=await kintone.api(kintone.api.url('/k/v1/apps.json',true),'GET',{limit:100});
      return {ok:true,apps:(r.apps||[]).map(x=>({appId:x.appId,name:x.name}))};
    }catch(e){return {ok:false,errorCode:String(e.code||'APPS_LIST_UNAVAILABLE').slice(0,80)}}})()`);
    if(!discovered?.ok)return {status:'apps_discovery_unavailable',errorCode:discovered?.errorCode,candidates:[]};
    const candidates=matchingApps(discovered.apps);
    const chosen=centerAppId?Number(centerAppId):candidates.length===1?candidates[0].appId:null;
    if(!chosen || !Number.isSafeInteger(chosen) || chosen<1){
      return {status:candidates.length?'selection_required':'not_provisioned',candidates};
    }
    if(!candidates.some(x=>x.appId===chosen))return {status:'app_not_found_or_not_named_batch_center',candidates};
    const result=await session.evalJS(`(async()=>{try{
       const app=${chosen};
       const [fields,plugins]=await Promise.all([
         kintone.api(kintone.api.url('/k/v1/app/form/fields.json',true),'GET',{app}),
         kintone.api(kintone.api.url('/k/v1/app/plugins.json',true),'GET',{app})
       ]);
       const outFields={};
       const all=fields.properties||{};
       for(const [key,p] of Object.entries(all)){
         outFields[key]={type:p.type};
         if(p.type==='SUBTABLE')outFields[key].fields=Object.fromEntries(Object.keys(p.fields||{}).map(x=>[x,true]));
       }
       return {ok:true,fields:outFields,pluginEnabled:(plugins.plugins||[]).some(x=>x.name==='ResoArc Batch Center'&&x.enabled===true)};
    }catch(e){return {ok:false,errorCode:String(e.code||'SCHEMA_OR_PLUGIN_QUERY_UNAVAILABLE').slice(0,80)}}})()`);
    if(!result.ok)return {status:'center_inspection_unavailable',appId:chosen,errorCode:result.errorCode,candidates};
    const expected=schemaFields(JSON.parse(fs.readFileSync(path.join(ROOT,'control-app','fields.json'),'utf8')));
    const schema=evaluateSchema(result.fields,expected);
    return {status:schema.ok&&result.pluginEnabled?'ready_for_control_app_e2e':'center_setup_incomplete',
      appId:chosen,pluginEnabled:result.pluginEnabled,schema,candidates};
  }finally{
    if(session)try{session.close();}catch{}
    if(tab)try{await browser.closeTab(tab.id);}catch{}
  }
}
async function run(options={}){
  const mr=(name)=>require(path.join(MR_ROOT,'integrations',name));
  const credential=mr('kintone-credentials');
  const auth=credential.status();
  const env=credential.resolve();
  const paths=[
    path.join(ROOT,'center-plugin','src'),
    path.join(ROOT,'center-plugin','release','resoarc-batch-center-v0.2.1.zip')
  ];
  const preflight=await mr('kintone-plugin-preflight').inspectMany(paths);
  const report={version:1,source:'ResoArc Clock + MR kintone test tools',
    timestamp:new Date().toISOString(),readOnly:true,releaseReady:false,
    preflight:{ok:preflight.ok,passed:preflight.passed,failed:preflight.failed,
      packageKinds:preflight.results.map(x=>x.packageType)},
    authConfigured:!!auth.configured,api:null,browser:null,center:null};
  if(!auth.configured || !env.KINTONE_APP_ID || !env.KINTONE_API_TOKEN){
    report.status='mr_credentials_not_configured';
    return report;
  }
  const gate=await mr('kintone-release-gate').runGate({
    paths:[],url:new URL('/k/'+Number(env.KINTONE_APP_ID)+'/',env.KINTONE_BASE_URL).toString(),
    checkApi:true,screenshot:false,probeTabs:false,save_report:false
  });
  report.api={ok:gate.checks.api.status==='passed',status:gate.checks.api.status,
    benchmark:gate.checks.api.benchmark};
  report.browser={ok:gate.checks.browser.ok,status:gate.checks.browser.status,
    exceptions:gate.checks.browser.exceptions?.length||0};
  try{
    report.center=await inspectCenter(mr('kintone-browser-backend'),env,options.centerAppId||process.env.BATCH_CENTER_APP_ID);
  }catch(err){report.center={status:'inspection_error',error:String(err.message||err).slice(0,130)};}
  report.status=(!preflight.ok||!report.api.ok||!report.browser.ok)?'mr_preflight_failed':
    report.center.status==='ready_for_control_app_e2e'?'staging_ready_for_control_app_e2e':'center_app_not_ready';
  if(options.saveReport!==false){
    try{report.reportPath=mr('kintone-report').saveReport('batch-center-readiness',report);}
    catch(err){report.reportSaveError='REPORT_SAVE_UNAVAILABLE';}
  }
  return report;
}
if(require.main===module){
  run().then(x=>{
    // Never print a token, cookie, or absolute report path.
    const {reportPath,...publicResult}=x;
    console.log(JSON.stringify({...publicResult,reportSaved:!!reportPath},null,2));
    if(x.status==='mr_preflight_failed')process.exitCode=1;
  }).catch(err=>{console.error('MR_BATCH_READINESS_ERROR: '+err.message);process.exitCode=2;});
}
module.exports={schemaFields,evaluateSchema,matchingApps,inspectCenter,run};
