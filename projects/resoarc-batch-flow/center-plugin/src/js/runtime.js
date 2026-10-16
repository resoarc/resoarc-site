/* ResoArc Batch Center kintone application plugin. MIT */
(function(){
 'use strict';
 const core=globalThis.ResoArcBatchFlow, center=globalThis.ResoArcBatchCenter;
 const api=(path,method,payload)=>kintone.api(kintone.api.url(path,true),method,payload);
 const value=v=>({value:v});
 const when=new Date().toISOString().replace('.000Z','Z');
 kintone.events.on(['app.record.create.submit','app.record.edit.submit'],function(event){
   const r=event.record;
   if(!r?.Steps||!r?.DailyTime||!r?.NextRunAt)return event;
   try{
     center.parseRecord(r,core);
     r.NextRunAt.value=center.nextScheduledRun(r,undefined,{reset:true});
     if(r.RunState&&!r.RunState.value)r.RunState.value='待機';
   }catch(err){event.error='ResoArc Batch Center: '+err.message;}
   return event;
 });
 kintone.events.on('app.record.detail.show',function(event){
   const r=event.record;
   if(!r?.Steps||!r?.DailyTime||!r?.RunState)return event;
   const header=kintone.app.record.getHeaderMenuSpaceElement();
   if(!header||header.querySelector('[data-ra-center]'))return event;
   const wrap=document.createElement('div');wrap.dataset.raCenter='1';
   wrap.style.cssText='border:1px solid #c3cfd7;background:#f7fafc;padding:12px;border-radius:8px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;';
   const title=document.createElement('b');title.textContent='ResoArc Batch Center';
   const test=document.createElement('button');test.type='button';test.textContent='処理をテスト（変更なし）';
   const run=document.createElement('button');run.type='button';run.textContent='このバッチを実行';
   const message=document.createElement('pre');message.style.cssText='flex-basis:100%;white-space:pre-wrap;margin:0;max-height:200px;overflow:auto;';
   const log=text=>{message.textContent+=text+'\n';};
   const app=kintone.app.getId(),id=r.$id.value;
   async function execute(dryRun){
     if(!dryRun&&!confirm('このバッチを実行します。途中失敗した場合、前の更新は戻りません。続行しますか？'))return;
     test.disabled=run.disabled=true;message.textContent='';
     try{
       const current=await api('/k/v1/record.json','GET',{app,id});
       const data=current.record;
       if(data.RunState?.value==='実行中')throw Error('現在実行中です。時間を置いて再確認してください');
       const flow=center.parseRecord(data,core);
       let revision=current.record.$revision.value;
       if(!dryRun){
         const claim=await api('/k/v1/record.json','PUT',{
           app,id,revision,record:{
             RunState:value('実行中'),
             RunToken:value((globalThis.crypto?.randomUUID?.()||'manual-'+Date.now())),
             LastStartedAt:value(new Date().toISOString().replace('.000Z','Z')),
             NextRunAt:value(center.nextScheduledRun(data))
           }
         });
         revision=claim.revision;
       }
       let output=null,error=null;
       try{
         output=await core.runFlow(flow,api,{dryRun,onProgress:item=>log('タスク'+item.number+' / '+item.type+' / '+item.count+'件 '+(item.success?'完了':'失敗'))});
       }catch(e){error=e;log('停止: '+e.message);}
       if(!dryRun){
         const entry={time:new Date().toISOString(),ok:!error,steps:output?.results.length||0,error:error?.message||''};
         const history=[JSON.stringify(entry),...(data.RunHistory?.value||'').split('\n').filter(Boolean)].slice(0,20).join('\n').slice(0,10000);
         await api('/k/v1/record.json','PUT',{app,id,revision,record:{
           RunState:value(error?'要確認':'正常終了'),
           ...(data.ScheduleType?.value==='一回'&&!error?{BatchEnabled:value('停止')}:{}),
           LastFinishedAt:value(new Date().toISOString().replace('.000Z','Z')),
           LastResult:value(error?'要確認: '+error.message:'正常終了'),
           RunHistory:value(history)
         }});
       }
       log(error?'失敗しました。データと状態を確認してください':dryRun?'テストが完了しました。本番データは変更していません':'実行が完了しました。ページを更新すると最新状態を確認できます');
     }catch(err){log('実行できません: '+err.message);}
     finally{test.disabled=run.disabled=false;}
   }
   test.addEventListener('click',()=>execute(true));run.addEventListener('click',()=>execute(false));
   wrap.append(title,test,run,message);header.append(wrap);
   return event;
 });
})();
