/* ResoArc Auto Number settings v1.1.0 / MIT */
(function(pluginId){
  'use strict';
  const $=id=>document.getElementById(id);
  const form=$('ra-config-form');
  const old=kintone.plugin.app.getConfig(pluginId)||{};
  const error=msg=>{$('ra-error').textContent=msg||'';};
  const app=kintone.app.getId();
  const api=(url,method,params)=>kintone.api(kintone.api.url(url,true),method,params);
  const target=$('ra-field');
  const prefix=$('ra-prefix'), width=$('ra-width'),start=$('ra-start');
  prefix.value=old.prefix||'';
  width.value=old.width||'6';start.value=old.start||'1';
  function chosen(){return target.selectedOptions && target.selectedOptions[0];}
  function preview(){
    let result='設定値を確認してください';
    try{
      if(!/^[1-9][0-9]{0,8}$/.test(start.value.trim()))throw Error();
      if(!/^[A-Za-z0-9_-]{0,20}$/.test(prefix.value))throw Error();
      result=prefix.value+BigInt(start.value.trim()).toString().padStart(Number(width.value),'0');
      if(chosen() && chosen().dataset.table)result+='-123';
    }catch(_){/* the validation error is shown when saving */}
    $('ra-preview-number').textContent=result;
    $('ra-preview-caption').textContent=chosen()?.dataset.table
      ? 'レコードID＝1・テーブル行ID＝123の場合'
      : 'レコードID＝1の場合';
  }
  [prefix,width,start,target].forEach(el=>el.addEventListener('change',preview));
  [prefix,start].forEach(el=>el.addEventListener('input',preview));
  async function init(){
    try{
      if(!app)throw Error('アプリIDを取得できません。');
      const response=await api('/k/v1/app/form/fields.json','GET',{app});
      target.replaceChildren();
      const placeholder=document.createElement('option');
      placeholder.value='';placeholder.textContent='フィールドを選択してください';
      target.appendChild(placeholder);
      function addOption(f,table,label){
        if(f.type!=='SINGLE_LINE_TEXT'||f.required||f.lookup||f.expression)return;
        const option=document.createElement('option');
        option.value=f.code;
        option.dataset.table=table||'';
        option.textContent=(table?label+' ＞ ':'')+f.label+' ('+f.code+')';
        target.appendChild(option);
      }
      for(const f of Object.values(response.properties||{})){
        if(f.type==='SUBTABLE'){
          for(const nested of Object.values(f.fields||{}))addOption(nested,f.code,f.label);
        }else addOption(f,'','');
      }
      const matching=Array.from(target.options).find(option=>option.value===old.field
        && (option.dataset.table||'')===(old.table||''));
      if(matching)target.value=matching.value;
      if(matching)matching.selected=true;
      if(target.options.length===1)error('採番可能な文字列（1行）フィールドがありません。');
      preview();
    }catch(err){
      error('フィールド情報の取得に失敗しました：'+(err.message||''));
    }
  }
  form.addEventListener('submit',event=>{
    event.preventDefault();error('');
    const option=chosen();
    const field=option?.value||'';
    const table=option?.dataset.table||'';
    if(!field){error('採番先フィールドを選択してください。');return;}
    if(!/^[A-Za-z0-9_-]{0,20}$/.test(prefix.value)){error('接頭辞は半角英数字・ハイフン・アンダースコアの20文字以内です。');return;}
    if(!/^(?:[3-9]|1[0-2])$/.test(width.value)){error('桁数は3～12の範囲で指定してください。');return;}
    if(!/^[1-9][0-9]{0,8}$/.test(start.value.trim())){error('開始番号は1～999999999の整数です。');return;}
    $('ra-save').disabled=true;
    kintone.plugin.app.setConfig({field,table,prefix:prefix.value,width:width.value,start:start.value.trim()});
  });
  $('ra-cancel').addEventListener('click',()=>window.history.back());
  init();
})(kintone.$PLUGIN_ID);