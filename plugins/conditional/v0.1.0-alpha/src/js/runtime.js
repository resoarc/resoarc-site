/* ResoArc Conditional Fields runtime v0.1.0-alpha / SPDX-License-Identifier: MIT */
(function(pluginId){
'use strict';
const raw = kintone.plugin.app.getConfig(pluginId) || {};
const core = typeof ResoArcConditional === 'undefined' ? null : ResoArcConditional;
const rules = core && core.normalize(raw.rules);
if (!rules) return;
const ownError='この条件では入力が必要です。';
const editing=['app.record.create','app.record.edit','mobile.app.record.create','mobile.app.record.edit'];
const detail=['app.record.detail.show','mobile.app.record.detail.show'];
function getApi(event) {
  return event.type.startsWith('mobile.') ? kintone.mobile?.app?.record : kintone.app?.record;
}
function shown(event) {
  try {
    const api = getApi(event);
    if (typeof api?.setFieldShown !== 'function') return event;
    for (const r of core.evaluate(rules,event.record)) {
      if (r.missing || !event.record[r.target]) {
        console.warn('[ResoArc Conditional] Missing source or target field:',r.target);
        continue;
      }
      api.setFieldShown(r.target,r.shown);
    }
  } catch(err) {
    console.error('[ResoArc Conditional] Visibility update failed:',err);
  }
  return event;
}
kintone.events.on([...editing.map(p=>p+'.show'),...detail],shown);
for (const driver of new Set(rules.map(r=>r.source))) {
  kintone.events.on(editing.map(p=>p+'.change.'+driver),shown);
}
kintone.events.on(editing.map(p=>p+'.submit'),event=>{
  try {
    // Fail closed if configuration references a deleted/inaccessible field:
    // it must not silently bypass required validation.
    const states = core.evaluate(rules,event.record);
    if (states.some(state=>state.missing || !event.record[state.target])) {
      event.error='条件付き表示の対象フィールドを確認できません。アプリ設定と権限をご確認ください。';
      return event;
    }
    const api=getApi(event);
    for (const state of states) {
      const target=event.record[state.target];
      if (state.required && core.empty(target.value)) {
        if(typeof api?.setFieldShown==='function')api.setFieldShown(state.target,true);
        target.error=ownError;
      } else if (target.error===ownError) {
        target.error=null;
      }
      // Do not clear hidden values or override validation errors from other apps.
    }
  } catch(err) {
    console.error('[ResoArc Conditional] Required validation failed:',err);
    event.error='条件付き入力チェックを完了できませんでした。';
  }
  return event;
});
})(kintone.$PLUGIN_ID);
