/* ResoArc Batch Flow desktop: manual execution under user session */
(function (pluginId) {
  'use strict';
  const raw=kintone.plugin.app.getConfig(pluginId)||{};
  if(!raw.flow)return;
  let flow;
  try{flow=JSON.parse(raw.flow);globalThis.ResoArcBatchFlow.validateFlow(flow);}catch(_){return;}
  kintone.events.on('app.record.index.show', function(event) {
    const header=kintone.app.getHeaderMenuSpaceElement();
    if(!header || header.querySelector('[data-ra-batch-root]'))return event;
    const root=document.createElement('section');root.className='ra-batch-panel';root.dataset.raBatchRoot='1';
    const label=document.createElement('strong');label.textContent='ResoArc Batch Flow：'+flow.name;
    const test=document.createElement('button');test.type='button';test.textContent='実行内容を確認（テスト）';
    const run=document.createElement('button');run.type='button';run.textContent='バッチを実行';
    const status=document.createElement('pre');status.className='ra-batch-status';status.setAttribute('aria-live','polite');
    const log=(m)=>{status.textContent+=m+'\n';};
    const transport=(url,method,params)=>kintone.api(kintone.api.url(url,true),method,params);
    async function execute(dryRun){
      if(!dryRun && !confirm('「'+flow.name+'」の更新・登録を実行します。前段の処理は失敗時に戻せません。実行しますか？'))return;
      test.disabled=run.disabled=true;status.textContent='';
      log(dryRun?'テスト実行：データは変更しません':'本番実行を開始します');
      try{
        const result=await globalThis.ResoArcBatchFlow.runFlow(flow,transport,{
          dryRun,onProgress:item=>log('タスク'+item.number+' '+(item.success?'完了':'失敗')+' / '+item.type+' / '+item.count+'件'+(item.error?' / '+item.error:''))
        });
        log('完了：'+result.results.length+'タスク');
      }catch(err){log('停止：'+err.message);}
      finally{test.disabled=run.disabled=false;}
    }
    test.addEventListener('click',()=>execute(true));
    run.addEventListener('click',()=>execute(false));
    root.append(label,test,run,status);
    header.append(root);
    return event;
  });
})(kintone.$PLUGIN_ID);
