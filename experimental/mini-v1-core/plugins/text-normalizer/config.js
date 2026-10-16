(function(pluginId){
  'use strict';
  const textarea=document.getElementById('settings'),message=document.getElementById('message');
  const config=kintone.plugin.app.getConfig(pluginId);
  textarea.value=config.settings||'{"rules":[]}';
  document.getElementById('save').addEventListener('click',function(){
    try {
      const parsed=JSON.parse(textarea.value);
      if(!Array.isArray(parsed?.rules)||parsed.rules.length<1||parsed.rules.length>20)throw Error('1〜20項目のルールが必要です');
      const seen=new Set();
      for(const rule of parsed.rules){
        if(!rule || typeof rule.field!=='string' || !rule.field || rule.field.length>128 ||
           /[\x00-\x1f]/.test(rule.field)||['__proto__','prototype','constructor'].includes(rule.field)||
           !['nfkc-trim','trim','spaces','phone'].includes(rule.mode)||seen.has(rule.field))throw Error('フィールドまたは変換設定が不正です');
        seen.add(rule.field);
      }
      message.textContent='保存しています';
      kintone.plugin.app.setConfig({settings:JSON.stringify({rules:parsed.rules})},function(){
        message.textContent='保存しました。アプリ設定を更新してください';
      });
    }catch(err){message.textContent=String(err.message||'設定エラー').slice(0,200)}
  });
})(kintone.$PLUGIN_ID);
