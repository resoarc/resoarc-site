/* ResoArc Batch Flow - shared browser/worker engine. MIT License. */
(function (root) {
  'use strict';
  const MAX_RECORDS = 100;
  const MAX_STEPS = 20;
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const plain = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
  const badKey = (k) => !k || ['__proto__', 'constructor', 'prototype', '$id', '$revision'].includes(k);
  const appId = (n) => Number.isSafeInteger(Number(n)) && Number(n) > 0;
  function verifyFields(obj, kind) {
    if (!plain(obj) || !Object.keys(obj).length) throw Error(kind + ' のフィールド指定が空です');
    for (const [dest, v] of Object.entries(obj)) {
      if (badKey(dest)) throw Error('使用できないフィールドコード: ' + dest);
      if (kind === '転記' && (typeof v !== 'string' || badKey(v))) throw Error('転記元はフィールドコードで指定してください');
      if (kind !== '転記' && !(v === null || ['string', 'boolean', 'number'].includes(typeof v) || (Array.isArray(v) && v.every(x => typeof x === 'string')))) {
        throw Error('設定値は文字列・数値・真偽値・null・文字列配列のみ対応します');
      }
    }
  }
  function validateFlow(flow) {
    if (!plain(flow) || !Array.isArray(flow.steps) || !flow.steps.length || flow.steps.length > MAX_STEPS) {
      throw Error('タスクは1～20件で指定してください');
    }
    if (typeof flow.name !== 'string' || !flow.name.trim() || flow.name.length > 100) throw Error('フロー名を指定してください');
    let lastRead = false;
    for (const [i, s] of flow.steps.entries()) {
      if (!plain(s) || !['read', 'update', 'copy', 'create'].includes(s.type)) throw Error((i + 1) + '番目のタスク種別が不正です');
      if (s.type !== 'update' && !appId(s.app)) throw Error((i + 1) + '番目のアプリIDが不正です');
      if (s.type === 'read') {
        if (typeof s.query !== 'string' || s.query.length > 1000 || /\b(?:limit|offset|order\s+by)\b/i.test(s.query)) {
          throw Error('抽出条件にlimit、offset、order byは指定できません');
        }
        lastRead = true;
      }
      if (s.type === 'update' || s.type === 'copy') {
        if (!lastRead) throw Error((i + 1) + '番目のタスクには前段の「レコード取得」が必要です');
        verifyFields(s.fields, s.type === 'copy' ? '転記' : '更新');
      }
      if (s.type === 'create') verifyFields(s.fields, '登録');
    }
    return flow;
  }
  const fieldValues = (fields) => {
    const record = {};
    for (const [k, v] of Object.entries(fields)) record[k] = {value: v};
    return record;
  };
  async function runFlow(flow, transport, options) {
    validateFlow(flow);
    if (typeof transport !== 'function') throw Error('APIアダプターを指定してください');
    const opts = options || {};
    const dryRun = opts.dryRun !== false;
    const results = [];
    let selected = [];
    let sourceApp = 0;
    const startedAt = new Date().toISOString();
    for (let index = 0; index < flow.steps.length; index++) {
      const task = flow.steps[index];
      const item = {number: index + 1, type: task.type, count: 0, dryRun};
      try {
        if (task.type === 'read') {
          const query = (task.query.trim() ? task.query.trim() + ' ' : '') + 'order by $id asc limit ' + (MAX_RECORDS + 1);
          const data = await transport('/k/v1/records.json', 'GET', {app: Number(task.app), query});
          if (!data || !Array.isArray(data.records)) throw Error('kintoneのレコード取得結果が不正です');
          if (data.records.length > MAX_RECORDS) throw Error('対象が100件を超えています。条件を絞ってください。この取得タスクでは更新しません');
          selected = data.records;
          sourceApp = Number(task.app);
          item.count = selected.length;
        } else if (task.type === 'update') {
          if (!sourceApp) throw Error('更新元アプリが未指定です');
          const records = selected.map(rec => {
            if (!rec.$id || !rec.$id.value) throw Error('レコードIDを取得できません');
            return {id: rec.$id.value, record: fieldValues(task.fields)};
          });
          item.count = records.length;
          if (!dryRun && records.length) await transport('/k/v1/records.json', 'PUT', {app: sourceApp, records});
          for (const rec of selected) {
            for (const [field, value] of Object.entries(task.fields)) rec[field] = {value};
          }
        } else if (task.type === 'copy') {
          const records = selected.map(rec => {
            const out = {};
            for (const [dest, src] of Object.entries(task.fields)) {
              if (!own(rec, src) || !rec[src] || !own(rec[src], 'value')) throw Error('転記元フィールドが見つかりません: ' + src);
              out[dest] = {value: rec[src].value};
            }
            return out;
          });
          item.count = records.length;
          if (!dryRun && records.length) await transport('/k/v1/records.json', 'POST', {app: Number(task.app), records});
        } else if (task.type === 'create') {
          item.count = 1;
          if (!dryRun) await transport('/k/v1/records.json', 'POST', {app: Number(task.app), records: [fieldValues(task.fields)]});
        }
        results.push(item);
        if (typeof opts.onProgress === 'function') opts.onProgress({...item, success: true});
      } catch (err) {
        const msg = 'タスク' + (index + 1) + 'で停止: ' + (err && err.message ? err.message : String(err));
        if (typeof opts.onProgress === 'function') opts.onProgress({...item, success: false, error: msg});
        const error = new Error(msg + '。前のタスクの変更は自動的には取り消されません');
        error.results = results;
        throw error;
      }
    }
    return {name: flow.name, dryRun, startedAt, finishedAt: new Date().toISOString(), results};
  }
  const api = {validateFlow, runFlow, MAX_RECORDS, MAX_STEPS};
  root.ResoArcBatchFlow = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
