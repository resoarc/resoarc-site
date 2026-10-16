/* ResoArc Clock: KV-backed adaptive polling. No external HTTP endpoint. MIT */
import {runFromCenter,e2eScope} from './center-runner.mjs';

const MAX_DUE=2;
const MAX_CANDIDATES=MAX_DUE+1;
const SYNC_MS=10*60*1000;
const WRITE_INTERVAL_MS=2*60*1000;
const keyFor=(id,scope,writes)=>'resoarc-clock:v1:app:'+id+
  (scope?':e2e:'+scope.id+':'+(writes?'write':'dry'):'');
const iso=d=>new Date(d).toISOString().replace('.000Z','Z');
const validMillis=t=>typeof t==='number'&&Number.isFinite(t)&&t>=0;

export async function runAdaptiveClock(env,transport,core,reference){
  if(!env.RA_CLOCK_STATE || typeof env.RA_CLOCK_STATE.get!=='function' || typeof env.RA_CLOCK_STATE.put!=='function')
    throw Error('適応型ポーリングにはCloudflare KVのRA_CLOCK_STATEバインディングが必要です');
  const app=Number(env.RA_CONTROL_APP_ID);
  if(!Number.isSafeInteger(app)||app<1)throw Error('RA_CONTROL_APP_IDが不正です');
  const now=reference?new Date(reference):new Date();
  const ts=now.getTime();
  if(!Number.isFinite(ts))throw Error('基準時刻が不正です');
  const scope=e2eScope(env);
  // E2E and normal schedules must never reuse each other's next-run cache.
  // The dry-run and write phases likewise get distinct initial sync states.
  const key=keyFor(app,scope,env.RA_ALLOW_WRITES==='true');
  // KV unavailable: do NOT silently fall back to costly one-minute kintone polling.
  const raw=await env.RA_CLOCK_STATE.get(key);
  let state=null;
  if(raw){
    try{
      const value=JSON.parse(raw);
      if(value.v===1&&validMillis(value.syncAt)&&validMillis(value.lastWriteAt)
         &&(value.nextDueAt===null||validMillis(value.nextDueAt))){
        state=value;
      }
    }catch(_){/* malformed data triggers a safe resync */}
  }
  if(state && ts < state.syncAt && (state.nextDueAt===null || ts<state.nextDueAt)){
    console.info('ResoArc Clock: cache hit, skipped kintone');
    return {polled:false,reason:'cached',outcomes:[]};
  }
  // One query retrieves overdue jobs AND the earliest future job. No separate due query.
  // A blank NextRunAt is not a scheduled job. Exclude it before the top-N sort,
  // otherwise draft records can fill the result window and starve real jobs.
  const query='BatchEnabled in ("有効") and RunState in ("待機","正常終了")'
    +' and NextRunAt != ""'+(scope?' and $id = "'+scope.id+'"':'')
    +' order by NextRunAt asc limit '+MAX_CANDIDATES;
  const data=await transport('/k/v1/records.json','GET',{app,query});
  if(!Array.isArray(data?.records))throw Error('実行予定検索の応答が不正です');
  const records=data.records;
  const due=records.filter(r=>{
    const t=Date.parse(r?.NextRunAt?.value||'');
    return Number.isFinite(t)&&t<=ts;
  }).slice(0,MAX_DUE);
  // runFromCenter accepts pre-fetched due records to eliminate a second kintone request.
  const outcomes=due.length?await runFromCenter(env,transport,core,now,{records:due}):[];

  // A full due batch may conceal more overdue jobs beyond the limit.
  // Continue checking every minute until the backlog is known to be clear.
  const backlogMayRemain=due.length===MAX_DUE;
  let nextDueAt=backlogMayRemain?ts:null;
  if(!backlogMayRemain){
    const future=records.map(r=>Date.parse(r?.NextRunAt?.value||''))
      .filter(t=>Number.isFinite(t)&&t>ts);
    const rescheduled=outcomes.map(r=>Date.parse(r?.nextRunAt||''))
      .filter(t=>Number.isFinite(t)&&t>ts);
    const futureTimes=[...future,...rescheduled];
    if(futureTimes.length)nextDueAt=Math.min(...futureTimes);
    // A due job that was not claimed (dry run or revision conflict) remains due.
    if(outcomes.some(x=>x.dryRun||x.skipped||!x.ok))nextDueAt=ts;
  }
  const syncAt=(!state||ts>=state.syncAt)?ts+SYNC_MS:state.syncAt;
  const shouldWrite=!state||ts-state.lastWriteAt>=WRITE_INTERVAL_MS||ts>=state.syncAt;
  if(shouldWrite){
    await env.RA_CLOCK_STATE.put(key,JSON.stringify({
      v:1,syncAt,nextDueAt,lastWriteAt:ts
    }));
  }
  console.info('ResoArc Clock: polled',due.length,'due;',outcomes.length,'evaluated');
  return {polled:true,due:due.length,outcomes,cacheUpdated:shouldWrite};
}
