/* ResoArc Batch Flow config. MIT */
(function (pluginId) {
  'use strict';
  const $ = id => document.getElementById(id);
  const core = globalThis.ResoArcBatchFlow;
  const stored = kintone.plugin.app.getConfig(pluginId) || {};
  let flow;
  try { flow = JSON.parse(stored.flow || 'null'); } catch (_) { flow = null; }
  const defaultApp = kintone.app.getId() || 1;
  if (!flow || !Array.isArray(flow.steps)) flow = {id:'batch-main', name:'新しいバッチ', timeJst:'03:00', steps:[{type:'read', app:defaultApp, query:''}]};
  $('ra-name').value = flow.name || '';
  $('ra-time').value = flow.timeJst || '03:00';
  const messages = {
    read:['レコード取得','対象アプリの条件に合うレコードを取得します。空欄なら全件（最大100件）。取得数が101件以上なら停止します。'],
    update:['取得レコードを更新','先に取得したレコードへ同じ値をセット。例：{"処理済":"はい"}'],
    copy:['別アプリへ転記','転記先フィールドコードをキー、元フィールドコードを値に指定。例：{"顧客名":"Customer"}'],
    create:['レコードを1件登録','フィールドコードをキー、登録する値を指定。例：{"件名":"日次実行"}']
  };
  function cell(tag, cls, text) {
    const el=document.createElement(tag); if(cls)el.className=cls; if(text)el.textContent=text; return el;
  }
  function button(label, action) { const b=cell('button','ra-small',label); b.type='button'; b.addEventListener('click',action); return b; }
  function renderTask(task) {
    const node=cell('article','ra-step');
    const top=cell('div','ra-step-head');
    const heading=cell('strong','',String($('ra-steps').children.length+1)+'. タスク');
    const type=cell('select','ra-type');
    for(const [value,arr] of Object.entries(messages)) {const opt=cell('option','',arr[0]);opt.value=value;type.append(opt);}
    type.value=task.type || 'read';
    const tools=cell('div','ra-step-tools');
    tools.append(button('↑',()=>{const prev=node.previousElementSibling;if(prev){prev.before(node);renumber();}}),
      button('↓',()=>{const next=node.nextElementSibling;if(next){next.after(node);renumber();}}),
      button('削除',()=>{node.remove();renumber();}));
    top.append(heading,type,tools);
    const desc=cell('p','ra-note');
    const appLabel=cell('label','ra-app-label','アプリID');
    const app=cell('input','ra-app');app.type='number';app.min='1';app.step='1';app.value=task.app||defaultApp;appLabel.append(app);
    const queryLabel=cell('label','ra-query-label','抽出条件（kintoneクエリ）');
    const query=cell('input','ra-query');query.placeholder='例：状況 = "未処理"';query.value=task.query||'';queryLabel.append(query);
    const fieldsLabel=cell('label','ra-fields-label','フィールド指定（JSON）');
    const fields=cell('textarea','ra-fields');fields.rows=3;fields.spellcheck=false;
    fields.value=JSON.stringify(task.fields||{},null,2);fieldsLabel.append(fields);
    const refresh=()=>{desc.textContent=messages[type.value][1];appLabel.hidden=type.value==='update';queryLabel.hidden=type.value!=='read';fieldsLabel.hidden=type.value==='read';};
    type.addEventListener('change',refresh);refresh();
    node.append(top,desc,appLabel,queryLabel,fieldsLabel);
    $('ra-steps').append(node);
  }
  function renumber(){[...$('ra-steps').children].forEach((el,i)=>{el.querySelector('strong').textContent=(i+1)+'. タスク';});}
  function cronFromJst(time){
    const m=/^([01]\d|2[0-3]):([0-5]\d)$/.exec(time);
    if(!m)throw Error('時刻はHH:MM形式で指定してください');
    const hh=(Number(m[1])+15)%24;
    return Number(m[2])+' '+hh+' * * *';
  }
  function collect(){
    const steps=[...$('ra-steps').children].map((node,i)=>{
      const type=node.querySelector('.ra-type').value;
      const out={type};
      if(type!=='update')out.app=Number(node.querySelector('.ra-app').value);
      if(type==='read')out.query=node.querySelector('.ra-query').value.trim();
      else {
        try{out.fields=JSON.parse(node.querySelector('.ra-fields').value);}catch(_){throw Error((i+1)+'番目のフィールド指定が正しいJSONではありません');}
      }
      return out;
    });
    const out={id:'batch-main', name:$('ra-name').value.trim(), timeJst:$('ra-time').value, cron:cronFromJst($('ra-time').value), steps};
    core.validateFlow(out);
    return out;
  }
  $('ra-add').addEventListener('click',()=>{if($('ra-steps').children.length>=20){$('ra-error').textContent='最大20タスクです';return;}renderTask({type:'read',app:defaultApp,query:''});});
  $('ra-form').addEventListener('submit', e=>{
    e.preventDefault(); $('ra-error').textContent='';
    try { const out=collect(); kintone.plugin.app.setConfig({flow:JSON.stringify(out)}); }
    catch(error){$('ra-error').textContent=error.message;}
  });
  $('ra-export').addEventListener('click',()=>{
    $('ra-error').textContent='';
    try {$('ra-json').value=JSON.stringify({workflows:[collect()]},null,2);}
    catch(error){$('ra-error').textContent=error.message;}
  });
  $('ra-cancel').addEventListener('click',()=>history.back());
  flow.steps.forEach(renderTask);
})(kintone.$PLUGIN_ID);
