/* ResoArc suite user interface: all input stays in this browser. */
(function () {
  'use strict';
  const root = document.querySelector('[data-resoarc-tool]');
  if (!root || !window.ResoArcSuite) return;
  const api = window.ResoArcSuite;
  const type = root.dataset.resoarcTool;
  const $ = id => document.getElementById(id);
  const primary = $('suite-primary'), secondary = $('suite-secondary'), settings = $('suite-settings');
  const run = $('suite-run'), output = $('suite-output'), state = $('suite-state');
  const download = $('suite-download'), print = $('suite-print'), preview = $('suite-preview');
  let result = null;
  function params() {
    let obj;
    try { obj = JSON.parse(settings.value || '{}'); }
    catch (e) { throw Error('設定JSONが正しくありません: ' + e.message); }
    if (!obj || Array.isArray(obj) || typeof obj !== 'object') throw Error('設定はJSONオブジェクトで指定してください');
    return obj;
  }
  async function content(input, required) {
    const file = input && input.files[0];
    if (!file) {
      if (required) throw Error('入力ファイルを指定してください');
      return null;
    }
    if (file.size > 12 * 1024 * 1024) throw Error('12 MB以下のファイルを指定してください');
    const text = await file.text();
    return api.loadText(text, file.name);
  }
  function rows(data) { return api.dataRows(data); }
  run.addEventListener('click', async () => {
    run.disabled = true; result = null; state.textContent = 'ブラウザー内で検査しています';
    download.hidden = true; print.hidden = true; preview.hidden = true;
    output.textContent = '';
    try {
      const cfg = params(), source = await content(primary, true);
      if (type === 'bulk-update') {
        const patch = await content(secondary, true);
        result = api.bulkPreview(rows(source), rows(patch), cfg.keyField || '$id');
      } else if (type === 'permission-audit') {
        result = api.permissionAudit(source);
      } else if (type === 'duplicates') {
        result = api.duplicateGroups(rows(source), cfg.fields || []);
      } else if (type === 'lookup-audit') {
        const master = await content(secondary, true);
        result = api.lookupAudit(rows(source), rows(master), cfg.sourceKey, cfg.masterKey, cfg.compareFields);
      } else if (type === 'aggregate') {
        result = api.aggregate(rows(source), cfg.dimension, cfg.metric, cfg.operation);
      } else if (type === 'report') {
        const html = api.reportHTML(rows(source), cfg.columns, cfg.title);
        preview.innerHTML = html; preview.hidden = false;
        result = { rowCount: rows(source).length, columns: cfg.columns || Object.keys(rows(source)[0]), printReady: true };
        print.hidden = false;
      } else throw Error('不明なツールです');
      const serialized = JSON.stringify(result, null, 2);
      output.textContent = serialized.length > 160000 ? serialized.slice(0, 160000) + '\n...長い結果はJSON保存で確認できます' : serialized;
      state.textContent = '完了。元データは変更していません。外部送信もありません。';
      download.hidden = false;
    } catch (error) {
      state.textContent = '入力を確認してください: ' + (error && error.message || String(error));
    } finally { run.disabled = false; }
  });
  download.addEventListener('click', () => {
    if (!result) return;
    const file = new Blob([JSON.stringify(result, null, 2) + '\n'], { type:'application/json;charset=utf-8' });
    const url = URL.createObjectURL(file);
    const a = document.createElement('a');
    a.href = url; a.download = 'resoarc-' + type + '-result.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
  });
  print.addEventListener('click', () => { if (!preview.hidden) window.print(); });
})();
