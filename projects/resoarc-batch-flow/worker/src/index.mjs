/* ResoArc Batch Flow - owner-managed Cloudflare Worker. MIT */
import '../../src/js/core.js';
import {runFromCenter} from './center-runner.mjs';
import {runAdaptiveClock} from './adaptive-clock.mjs';
const core = globalThis.ResoArcBatchFlow;
function hostname(domain) {
  if (typeof domain !== 'string' || domain.length > 253 || !/^[a-zA-Z0-9.-]+$/.test(domain) || domain.includes('..')) {
    throw Error('KINTONE_DOMAINにはホスト名のみを設定してください');
  }
  if (!/(?:^|\.)(?:cybozu\.com|kintone\.com)$/.test(domain)) {
    throw Error('許可されたkintoneドメインではありません');
  }
  return domain;
}
export function adapter(env) {
  const host=hostname(env.KINTONE_DOMAIN);
  const tokens=env.KINTONE_API_TOKENS;
  if (!tokens || !/^[A-Za-z0-9,]+$/.test(tokens)) throw Error('APIトークンをSecretに設定してください');
  return async (path, method, params) => {
    if(!((path==='/k/v1/records.json' && ['GET','POST','PUT'].includes(method)) || (path==='/k/v1/record.json' && ['GET','PUT'].includes(method)))) throw Error('未対応のAPIです');
    const url=new URL('https://'+host+path);
    const init={method, headers:{'X-Cybozu-API-Token':tokens, 'Accept':'application/json'}};
    if(method==='GET') {
      url.searchParams.set('app',String(params.app));
      if(path==='/k/v1/record.json'){
        if(!params.id)throw Error('単一レコード取得にはレコードIDが必要です');
        url.searchParams.set('id',String(params.id));
      }else if(typeof params.query==='string')url.searchParams.set('query',params.query);
    }else{
      init.headers['Content-Type']='application/json';
      init.body=JSON.stringify(params);
    }
    const response=await fetch(url.toString(),init);
    if(!response.ok){
      // Preserve the code, but never expose a potentially sensitive response body.
      let code=null;
      try{
        const failure=await response.json();
        if(typeof failure?.code==='string')code=failure.code.slice(0,80);
      }catch(_){}
      const error=new Error('kintone API '+response.status+'（トークン権限と設定を確認）');
      error.status=response.status;
      error.kintoneCode=code;
      throw error;
    }
    return response.json();
  };
}
function parseWorkflows(env) {
  if(!env.WORKFLOWS_JSON)throw Error('WORKFLOWS_JSONをSecretに設定してください');
  const decoded=JSON.parse(env.WORKFLOWS_JSON);
  if(!decoded || !Array.isArray(decoded.workflows) || decoded.workflows.length<1 || decoded.workflows.length>20)throw Error('workflowsは1～20件です');
  const seen=new Set();
  for(const f of decoded.workflows){
    core.validateFlow(f);
    if(typeof f.cron!=='string' || !/^\d{1,2} \d{1,2} \* \* \*$/.test(f.cron))throw Error('cronは日次形式で指定してください');
    if(typeof f.id!=='string' || !/^[a-zA-Z0-9_-]{1,60}$/.test(f.id) || seen.has(f.id))throw Error('フローIDは重複不可です');
    seen.add(f.id);
  }
  return decoded.workflows;
}
export default {
  async scheduled(controller,env,ctx) {
    // Fail closed: scheduled execution is impossible until explicitly enabled.
    if(env.RA_CLOCK_ENABLED!=='true'){
      console.info('ResoArc Clock is disabled');
      return;
    }
    // Never allow the legacy JSON workflow route to bypass an E2E-only app/batch scope.
    if((env.RA_E2E_ONLY_BATCH_ID!==undefined || env.RA_E2E_ALLOWED_APP_ID!==undefined) && !env.RA_CONTROL_APP_ID)
      throw Error('E2E限定設定では管理アプリIDが必須です');
    if(env.RA_CONTROL_APP_ID) {
      // A newly enabled write flag must not silently turn all registered jobs
      // into writable targets. Unscoped production writes need a second opt-in.
      if(env.RA_ALLOW_WRITES==='true' &&
        !(env.RA_E2E_ONLY_BATCH_ID && env.RA_E2E_ALLOWED_APP_ID) &&
        env.RA_ALLOW_UNSCOPED_WRITES!=='true'){
        throw Error('Unscoped write execution requires RA_ALLOW_UNSCOPED_WRITES=true');
      }
      const transport=adapter(env);
      if(env.RA_POLL_MODE==='adaptive')return runAdaptiveClock(env,transport,core);
      if(!env.RA_POLL_MODE||env.RA_POLL_MODE==='minute')return runFromCenter(env,transport,core);
      throw Error('RA_POLL_MODEにはadaptiveまたはminuteを明示してください');
    }
    const flows=parseWorkflows(env).filter(f=>f.cron===controller.cron);
    if (!flows.length){console.info('該当するフローなし: '+controller.cron);return;}
    const transport=adapter(env);
    const dryRun=env.RA_ALLOW_WRITES!=='true';
    for(const flow of flows){
      console.info('開始:',flow.id,'dryRun:',dryRun);
      try{
        const result=await core.runFlow(flow,transport,{
          dryRun,
          onProgress: item=>console.info('task',item.number,item.type,item.count,item.success?'ok':'failed')
        });
        console.info('完了:',flow.id,result.results.length,'tasks');
      }catch(err){
        console.error('停止:',flow.id,err.message);
        throw err; // Cloudflare Logs に失敗を残す。後続は実行しない
      }
    }
  },
  async fetch() {
    return new Response('ResoArc Batch Flow has no public execution endpoint.',{status:404});
  }
};
