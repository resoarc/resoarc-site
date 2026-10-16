/* ResoArc Batch Center: record adapter and Japan time scheduler. MIT */
(function(root){
  'use strict';
  const get=(record,key)=>record?.[key]?.value;
  function nextRunAt(time,reference){
    if(typeof time!=='string'||!/^([01]\d|2[0-3]):[0-5]\d$/.test(time))throw Error('実行時刻はHH:mm形式にしてください');
    const now=reference?new Date(reference):new Date();
    if(!Number.isFinite(now.getTime()))throw Error('基準日時が不正です');
    const parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).filter(x=>x.type!=='literal').map(x=>[x.type,Number(x.value)]));
    const [hour,minute]=time.split(':').map(Number);
    const todayMs=Date.UTC(parts.year,parts.month-1,parts.day,hour-9,minute,0);
    return new Date(todayMs>now.getTime()?todayMs:todayMs+86400000).toISOString().replace('.000Z','Z');
  }
  // Optional fields preserve compatibility with existing daily-only control apps.
  // For interval jobs, missed ticks are coalesced into one run (no burst catch-up).
  function nextScheduledRun(record,reference,options){
    const mode=get(record,'ScheduleType')||'毎日';
    if(mode==='毎日')return nextRunAt(get(record,'DailyTime'),reference);
    if(mode==='一回'){
      const date=get(record,'OneTimeAt');
      const at=Date.parse(date||'');
      if(!Number.isFinite(at))throw Error('一回実行日時を指定してください');
      return new Date(at).toISOString().replace('.000Z','Z');
    }
    if(mode!=='間隔')throw Error('スケジュール種別は「毎日」「間隔」「一回」のいずれかにしてください');
    const minutes=Number(get(record,'IntervalMinutes'));
    if(!Number.isSafeInteger(minutes)||minutes<1||minutes>10080)throw Error('実行間隔は1～10080分で指定してください');
    const now=reference?new Date(reference):new Date();
    const t=now.getTime();
    if(!Number.isFinite(t))throw Error('基準日時が不正です');
    const planned=options?.reset?null:get(record,'NextRunAt');
    const anchor=planned?Date.parse(planned):NaN;
    const period=minutes*60000;
    const next=Number.isFinite(anchor)?(anchor>t?anchor:anchor+(Math.floor((t-anchor)/period)+1)*period):t+period;
    return new Date(next).toISOString().replace('.000Z','Z');
  }
  function parseRecord(record,core){
    const rows=get(record,'Steps');
    if(!Array.isArray(rows))throw Error('処理タスクのサブテーブルが見つかりません');
    const steps=rows.map((r,i)=>{
      const item=r?.value||{};
      const labels={'取得':'read','更新':'update','転記':'copy','登録':'create'};
      const type=labels[item.TaskType?.value]||item.TaskType?.value;
      const out={type};
      if(type!=='update')out.app=Number(item.TargetApp?.value);
      if(type==='read')out.query=item.Query?.value||'';
      else{
        try{out.fields=JSON.parse(item.FieldsJSON?.value||'{}');}
        catch(_){throw Error('タスク'+(i+1)+'の項目設定JSONが不正です');}
      }
      return out;
    });
    const result={id:'center-'+get(record,'$id'),name:get(record,'BatchName'),steps};
    core.validateFlow(result);
    return result;
  }
  const api={nextRunAt,nextScheduledRun,parseRecord};
  root.ResoArcBatchCenter=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
