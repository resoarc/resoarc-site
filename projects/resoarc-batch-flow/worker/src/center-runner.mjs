/* ResoArc Clock / Batch Center: one-minute scheduled dispatch. MIT */
import '../../control-app/control.js';
const center=globalThis.ResoArcBatchCenter;
const kfield=value=>({value});
// Workers Free allows at most 50 subrequests per invocation.
// 1 search + 2 * (claim + 20 step requests + finalize) = 45 maximum.
const MAX_DUE_PER_TICK=2;
function timeISO(value){return new Date(value).toISOString().replace('.000Z','Z');}
function logValue(old,entry){
  return [JSON.stringify(entry),...(old||'').split('\n').filter(Boolean)].slice(0,20).join('\n').slice(0,10000);
}
function makePatch(record,entry){
  return {
    RunState:kfield('要確認'),
    LastFinishedAt:kfield(timeISO(Date.now())),
    LastResult:kfield('要確認：'+entry.error),
    RunHistory:kfield(logValue(record.RunHistory?.value,entry))
  };
}
export async function runFromCenter(env,transport,core,reference,options){
  const controlApp=Number(env.RA_CONTROL_APP_ID);
  if(!Number.isSafeInteger(controlApp)||controlApp<1)throw Error('RA_CONTROL_APP_IDを設定してください');
  const now=reference?new Date(reference):new Date();
  if(!Number.isFinite(now.getTime()))throw Error('現在時刻が不正です');
  const at=timeISO(now);
  const query='BatchEnabled in ("有効") and RunState in ("待機","正常終了") and NextRunAt != "" and NextRunAt <= "'+at+'" order by NextRunAt asc limit '+(MAX_DUE_PER_TICK+1);
  const result=options&&Array.isArray(options.records)
    ?{records:options.records}
    :await transport('/k/v1/records.json','GET',{app:controlApp,query});
  if(!result||!Array.isArray(result.records))throw Error('バッチ管理アプリの検索に失敗しました');
  if(result.records.length>MAX_DUE_PER_TICK)console.warn('ResoArc Clock: 実行待ちが'+MAX_DUE_PER_TICK+'件を超えています。次の周期で再確認します');
  const dryRun=env.RA_ALLOW_WRITES!=='true';
  const outcomes=[];
  for(const rec of result.records.slice(0,MAX_DUE_PER_TICK)){
    const id=rec?.$id?.value;
    const rev=rec?.$revision?.value;
    if(!id||!rev){console.error('制御レコードIDまたはリビジョンがありません');continue;}
    let flow,next;
    try{
      flow=center.parseRecord(rec,core);
      next=center.nextScheduledRun(rec,now);
    }catch(err){
      const entry={time:at,ok:false,tasks:0,error:'バッチ定義エラー: '+err.message};
      console.error('バッチ定義が不正:',id,err.message);
      if(!dryRun){
        try{
          await transport('/k/v1/record.json','PUT',{
            app:controlApp,id,revision:rev,record:makePatch(rec,entry)
          });
        }catch(claimError){
          console.warn('定義エラーの記録に失敗:',id,claimError.message);
        }
      }
      outcomes.push({id,ok:false,error:entry.error});
      continue;
    }
    if(dryRun){
      console.info('ResoArc Clock DRY RUN:',id,flow.name,flow.steps.length,'tasks');
      try{
        const executed=await core.runFlow(flow,transport,{dryRun:true});
        outcomes.push({id,ok:true,dryRun:true,tasks:executed.results.length});
      }catch(err){
        console.error('プレビュー失敗:',id,err.message);
        outcomes.push({id,ok:false,dryRun:true,error:err.message});
      }
      continue;
    }
    const token=crypto.randomUUID();
    let claim;
    try{
      claim=await transport('/k/v1/record.json','PUT',{
        app:controlApp,id,revision:rev,
        record:{RunState:kfield('実行中'),RunToken:kfield(token),LastStartedAt:kfield(at),NextRunAt:kfield(next)}
      });
    }catch(err){
      // Only an actual revision conflict can be treated as another worker winning.
      if(err?.status!==409)throw err;
      console.warn('他の実行によって取得済み:',id,err.message);
      outcomes.push({id,ok:false,skipped:true});
      continue;
    }
    let error=null,taskCount=0;
    try{
      const executed=await core.runFlow(flow,transport,{dryRun:false});
      taskCount=executed.results.length;
    }catch(err){
      error=err;
      taskCount=Array.isArray(err.results)?err.results.length:0;
    }
    const entry={time:at,ok:!error,tasks:taskCount,error:error?.message||''};
    const patch={
      RunState:kfield(error?'要確認':'正常終了'),
      ...(rec.ScheduleType?.value==='一回'&&!error?{BatchEnabled:kfield('停止')}:{}),
      LastFinishedAt:kfield(timeISO(Date.now())),
      LastResult:kfield(error?'要確認：'+error.message:'正常終了（'+taskCount+'タスク）'),
      RunHistory:kfield(logValue(rec.RunHistory?.value,entry))
    };
    // A finalize conflict must not silently trigger business steps again.
    await transport('/k/v1/record.json','PUT',{app:controlApp,id,revision:claim.revision,record:patch});
    outcomes.push({id,ok:!error,tasks:taskCount,error:error?.message,
      nextRunAt:!error&&rec.ScheduleType?.value!=='一回'?next:null});
    if(error)console.error('ResoArc Clock: 手動確認が必要:',id,error.message);
  }
  return outcomes;
}
