/*
 * ResoArc Auto Number v1.1.0
 * SPDX-License-Identifier: MIT
 * Deterministic numbering; table rows use stable kintone row IDs, not screen positions.
 */
(function (global, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (global) global.ResoArcAutoNumber = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  function validConfig(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const field = String(raw.field || '').trim();
    const table = String(raw.table || '').trim();
    const prefix = String(raw.prefix || '');
    const width = Number(raw.width);
    const start = String(raw.start || '1');
    if (!field || field.length > 128 || table.length > 128 || (table && table === field)
      || !/^[A-Za-z0-9_-]{0,20}$/.test(prefix)
      || !Number.isInteger(width) || width < 3 || width > 12
      || !/^[1-9][0-9]{0,8}$/.test(start)) return null;
    return { field, table, prefix, width, start };
  }
  function makeNumber(recordId, raw) {
    const c = validConfig(raw);
    const id = String(recordId);
    if (!c || !/^[1-9][0-9]*$/.test(id)) throw new Error('設定またはレコードIDが不正です。');
    const result = c.prefix + (BigInt(id) + BigInt(c.start) - 1n).toString().padStart(c.width, '0');
    if (result.length > 64) throw new Error('採番文字列が64文字を超えています。');
    return result;
  }
  function makeRowNumber(recordId, rowId, raw) {
    const rid = String(rowId);
    if (!/^[1-9][0-9]*$/.test(rid)) throw new Error('テーブル行IDが不正です。');
    const result = makeNumber(recordId, raw) + '-' + rid;
    if (result.length > 64) throw new Error('採番文字列が64文字を超えています。');
    return result;
  }
  function isEmpty(value) { return value === '' || value === null || typeof value === 'undefined'; }
  // This routine is pure: retains every row ID and changes only empty target cells.
  function planUpdate(recordId, record, raw) {
    const c = validConfig(raw);
    if (!c || !record || typeof record !== 'object') throw new Error('レコードまたは設定が不正です。');
    const result = {record: {}, numbers: [], updated: false};
    if (!c.table) {
      const target = record[c.field];
      if (!target) throw new Error('採番フィールドが存在しません。');
      if (isEmpty(target.value)) {
        const number = makeNumber(recordId, c);
        result.record[c.field] = { value: number };
        result.numbers.push(number);
        result.updated = true;
      } else result.numbers.push(String(target.value));
      return result;
    }
    const target = record[c.table];
    if (!target || target.type !== 'SUBTABLE' || !Array.isArray(target.value)) throw new Error('採番対象のテーブルが存在しません。');
    const rows = target.value;
    const patch = [];
    const known = new Set();
    for (const row of rows) {
      if (!row || !/^[1-9][0-9]*$/.test(String(row.id)) || !row.value || !row.value[c.field])
        throw new Error('テーブルの行IDまたは採番フィールドを取得できません。');
      const current = row.value[c.field].value;
      const number = isEmpty(current) ? makeRowNumber(recordId, row.id, c) : String(current);
      if (known.has(number)) throw new Error('テーブル内に重複番号があります。処理を中止しました。');
      known.add(number);
      result.numbers.push(number);
      const item = {id: String(row.id)};
      if (isEmpty(current)) {
        item.value = {[c.field]: { value: number }};
        result.updated = true;
      }
      patch.push(item);
    }
    // All existing rows must be supplied or kintone deletes omitted rows.
    if (result.updated) result.record[c.table] = {value: patch};
    return result;
  }
  return {validConfig,makeNumber,makeRowNumber,isEmpty,planUpdate};
});

/*
 * ResoArc Auto Number runtime v1.1.0 / MIT
 * Same-origin GET/PUT only; preserves all existing table rows.
 */
(function(pluginId){
  'use strict';
  const raw = kintone.plugin.app.getConfig(pluginId);
  const core = typeof ResoArcAutoNumber !== 'undefined' ? ResoArcAutoNumber : null;
  const opts = core && core.validConfig(raw);
  if (!opts) return;
  function targetFields(record) {
    if (!record) return [];
    if (!opts.table) return record[opts.field] ? [record[opts.field]] : [];
    const t = record[opts.table];
    if (!t || !Array.isArray(t.value)) return [];
    return t.value.map(row=>row.value && row.value[opts.field]).filter(Boolean);
  }
  const showTypes=['app.record.create.show','mobile.app.record.create.show','app.record.edit.show','mobile.app.record.edit.show'];
  kintone.events.on(showTypes,event=>{
    const creating=event.type.includes('.create.');
    for(const f of targetFields(event.record)){
      f.disabled=true;
      if(creating)f.value='';
    }
    return event;
  });
  kintone.events.on(['app.record.create.submit','mobile.app.record.create.submit'],event=>{
    for(const f of targetFields(event.record))f.value='';
    return event;
  });
  const endpoint=()=>kintone.api.url('/k/v1/record.json',true);
  async function assignIfBlank(appId,recordId){
    const app=Number(appId),id=String(recordId||'');
    if(!Number.isSafeInteger(app)||app<=0||!/^[1-9][0-9]*$/.test(id))throw Error('レコードIDを取得できません。');
    // Retry once on optimistic revision conflicts. Never overwrite an existing number.
    for(let attempt=0;attempt<2;attempt++){
      const response=await kintone.api(endpoint(),'GET',{app,id});
      const rec=response && response.record;
      if(!rec || !rec.$revision)throw Error('レコードの取得に失敗しました。');
      const planned=core.planUpdate(id,rec,opts);
      if(!planned.updated)return {numbers:planned.numbers,updated:false};
      try{
        await kintone.api(endpoint(),'PUT',{
          app,id,record:planned.record,revision:rec.$revision.value
        });
        return {numbers:planned.numbers,updated:true};
      }catch(err){
        const code=String(err && err.code||'');
        if(attempt===0 && (code==='GAIA_RE20'||code==='GAIA_CO02'))continue;
        throw err;
      }
    }
    throw Error('競合を解消できませんでした。');
  }
  async function onSaved(event){
    try{await assignIfBlank(event.appId,event.recordId);}
    catch(err){
      console.error('[ResoArc Auto Number]',err);
      window.alert('レコードは保存されましたが、採番が完了していません。詳細画面の「採番を再試行」をご利用ください。\n'+(err?.message||'権限・通信状態を確認してください。'));
    }
    return event;
  }
  kintone.events.on(['app.record.create.submit.success','mobile.app.record.create.submit.success','app.record.edit.submit.success','mobile.app.record.edit.submit.success'],onSaved);
  function hasBlank(record){
    return targetFields(record).some(f=>core.isEmpty(f.value));
  }
  function container(mobile){
    if(mobile)return kintone.mobile?.app?.getHeaderSpaceElement?.() || null;
    return kintone.app?.record?.getHeaderMenuSpaceElement?.() || null;
  }
  kintone.events.on(['app.record.detail.show','mobile.app.record.detail.show'],event=>{
    const space=container(event.type.startsWith('mobile.'));
    if(!space)return event;
    const previous=space.querySelector('[data-resoarc-auto-number]');
    if(previous)previous.remove();
    if(!hasBlank(event.record))return event;
    const banner=document.createElement('div');
    banner.className='ra-number-notice';
    banner.setAttribute('data-resoarc-auto-number','');
    banner.setAttribute('role','status');
    const label=document.createElement('span');
    label.textContent='採番が未完了の項目があります。';
    const retry=document.createElement('button');
    retry.type='button';retry.className='ra-number-retry';
    retry.textContent='採番を再試行';
    retry.addEventListener('click',async()=>{
      retry.disabled=true;label.textContent='採番中…';
      try{await assignIfBlank(event.appId,event.recordId || event.record?.$id?.value);window.location.reload();}
      catch(err){
        label.textContent='採番できませんでした。編集権限と通信状態を確認してください。';
        console.error('[ResoArc Auto Number]',err);
        retry.disabled=false;
      }
    });
    banner.append(label,retry);space.appendChild(banner);
    return event;
  });
  if(typeof window!=='undefined' && window.__RESOARC_TEST__)window.__RESOARC_TEST__.assignIfBlank=assignIfBlank;
})(kintone.$PLUGIN_ID);