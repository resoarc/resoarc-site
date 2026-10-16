/* ResoArc: local-only, read-only data utilities. MIT License. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ResoArcSuite = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  function parseDelimited(text, delimiter) {
    const input = String(text || '').replace(/^\uFEFF/, '');
    const sep = delimiter || (input.split(/\r?\n/, 1)[0].includes('\t') ? '\t' : ',');
    if (sep !== ',' && sep !== '\t') throw Error('CSV/TSV の区切り文字が不正です');
    let rows = [], cells = [], cur = '', quoted = false, closed = false;
    for (let i = 0; i < input.length; i++) {
      const c = input[i];
      if (quoted) {
        if (c === '"' && input[i + 1] === '"') { cur += '"'; i++; }
        else if (c === '"') { quoted = false; closed = true; }
        else cur += c;
      } else if (c === '"' && !cur && !closed) { quoted = true; }
      else if (c === '"' && !quoted) { throw Error('CSVの引用符が不正な位置にあります'); }
      else if (c === sep) { cells.push(cur); cur = ''; closed = false; }
      else if (c === '\r' || c === '\n') {
        if (c === '\r' && input[i + 1] === '\n') i++;
        cells.push(cur); cur = ''; closed = false;
        if (cells.some(v => v !== '') || cells.length > 1) rows.push(cells);
        cells = [];
      } else if (closed && c !== ' ' && c !== '\t') { throw Error('閉じ引用符の後に余分な文字があります'); }
      else if (!closed) { cur += c; }
    }
    if (quoted) throw Error('CSVの引用符が閉じていません');
    if (cur || cells.length || closed) { cells.push(cur); rows.push(cells); }
    if (!rows.length) return [];
    const headers = rows.shift().map(h => h.trim());
    if (headers.some(h => !h) || new Set(headers).size !== headers.length) throw Error('見出しが空欄、または重複しています');
    return rows.map((cells, i) => {
      if (cells.length !== headers.length) throw Error('データ行' + (i + 2) + ': 列数が一致しません');
      return Object.fromEntries(headers.map((h, j) => [h, cells[j]]));
    });
  }
  function unwrap(v) {
    if (v && typeof v === 'object' && !Array.isArray(v) && own(v, 'value')) {
      return unwrap(v.value);
    }
    if (Array.isArray(v)) return v.map(unwrap);
    return v;
  }
  function dataRows(data) {
    const rows = Array.isArray(data) ? data : data && Array.isArray(data.records) ? data.records : null;
    if (!rows) throw Error('JSONにはレコード配列、または records 配列が必要です');
    if (rows.length > 50000) throw Error('安全上、50,000件を超えるファイルは扱えません。分割してください');
    return rows.map((r, i) => {
      if (!r || typeof r !== 'object' || Array.isArray(r)) throw Error('行' + (i + 1) + 'がオブジェクトではありません');
      return Object.fromEntries(Object.entries(r).map(([k, v]) => [k, unwrap(v)]));
    });
  }
  function loadText(input, fileName) {
    const str = String(input || '').trim();
    const file = String(fileName || '').toLowerCase();
    const json = /\.json$/.test(file) || (!/\.(csv|tsv|txt)$/.test(file) && /^[\[{]/.test(str));
    return json ? JSON.parse(str) : parseDelimited(input);
  }
  function clean(value) {
    return String(value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : value).normalize('NFKC').trim().toLowerCase();
  }
  function keyOf(v) { return JSON.stringify(v); }
  function uniqueIndex(rows, key, label) {
    const out = new Map();
    for (let i = 0; i < rows.length; i++) {
      const v = rows[i][key];
      if (v == null || String(v).trim() === '') throw Error(label + '行' + (i + 1) + 'の照合キーが空欄です');
      const id = keyOf(v);
      if (out.has(id)) throw Error(label + 'の照合キーが重複しています: ' + String(v));
      out.set(id, { row: rows[i], index: i });
    }
    return out;
  }
  function bulkPreview(baseline, changes, key) {
    const a = dataRows(baseline), b = dataRows(changes), field = key || '$id';
    const idx = uniqueIndex(a, field, '既存データ'), seen = new Set(), diffs = [], unmatched = [];
    for (const update of b) {
      const id = keyOf(update[field]);
      if (update[field] == null || String(update[field]).trim() === '') throw Error('更新データの照合キーが空欄です');
      if (seen.has(id)) throw Error('更新データの照合キーが重複しています');
      seen.add(id);
      const original = idx.get(id);
      if (!original) { unmatched.push(update[field]); continue; }
      const fields = [];
      for (const [name, after] of Object.entries(update)) {
        if (name === field) continue;
        const before = original.row[name];
        if (JSON.stringify(before) !== JSON.stringify(after)) fields.push({ field: name, before: before === undefined ? null : before, after });
      }
      if (fields.length) diffs.push({ key: update[field], fields });
    }
    return { mode: 'DRY_RUN_ONLY', keyField: field, sourceCount: a.length, patchCount: b.length, changedRecords: diffs.length, changes: diffs, unmatched, warnings: unmatched.length ? ['照合できないレコードがあります。変更は実行されていません。'] : [], writeExecuted: false };
  }
  function duplicateGroups(source, fields) {
    const rows = dataRows(source);
    if (!Array.isArray(fields) || !fields.length || fields.length > 20 || fields.some(f => typeof f !== 'string' || !f || f.length > 128) || new Set(fields).size !== fields.length) throw Error('比較するフィールドを1～20個、重複なしで指定してください');
    const groups = new Map(), ignoredRows = [];
    rows.forEach((row, i) => {
      const values = fields.map(f => clean(row[f]));
      if (values.every(x => !x)) { ignoredRows.push(i + 1); return; }
      const id = keyOf(values);
      if (!groups.has(id)) groups.set(id, { values: Object.fromEntries(fields.map((f, j) => [f, values[j]])), rowNumbers: [] });
      groups.get(id).rowNumbers.push(i + 1);
    });
    const found = [...groups.values()].filter(x => x.rowNumbers.length > 1);
    return { inspected: rows.length, comparedFields: fields, duplicateGroups: found.length, groups: found, ignoredRows, modified: false };
  }
  function lookupAudit(source, master, sourceKey, masterKey, compareFields) {
    if (![sourceKey, masterKey].every(k => typeof k === 'string' && k.length >= 1 && k.length <= 128)) throw Error('照合キーはソース側とマスタ側の両方を指定してください');
    if (compareFields != null && (typeof compareFields !== 'object' || Array.isArray(compareFields))) throw Error('比較フィールドの対応表が不正です');
    const rows = dataRows(source), targets = dataRows(master), idx = new Map(), duplicateMasterKeys = new Set();
    for (const target of targets) {
      const k = clean(target[masterKey]);
      if (!k) continue;
      if (idx.has(k)) duplicateMasterKeys.add(k);
      else idx.set(k, target);
    }
    const issues = [];
    rows.forEach((row, i) => {
      const k = clean(row[sourceKey]);
      if (!k) { issues.push({ row: i + 1, type: 'empty-key' }); return; }
      if (duplicateMasterKeys.has(k)) { issues.push({ row: i + 1, key: row[sourceKey], type: 'ambiguous-master' }); return; }
      const target = idx.get(k);
      if (!target) { issues.push({ row: i + 1, key: row[sourceKey], type: 'not-found' }); return; }
      for (const [local, remote] of Object.entries(compareFields || {})) {
        if (clean(row[local]) !== clean(target[remote])) issues.push({ row: i + 1, key: row[sourceKey], type: 'value-mismatch', field: local, expectedFrom: remote, actual: row[local], masterValue: target[remote] });
      }
    });
    return { checkedRows: rows.length, masterRows: targets.length, duplicateMasterKeys: [...duplicateMasterKeys], issueCount: issues.length, issues, repaired: false };
  }
  function aggregate(source, dimension, metric, operator) {
    const rows = dataRows(source), op = operator || 'sum';
    if (!['sum', 'count', 'average', 'min', 'max'].includes(op)) throw Error('集計種別が不明です');
    if (!dimension) throw Error('グループ化フィールドが必要です');
    if (op !== 'count' && !metric) throw Error('数値フィールドが必要です');
    const out = new Map(), invalid = [];
    rows.forEach((r, i) => {
      const k = String(r[dimension] == null ? '(空欄)' : r[dimension]);
      if (!out.has(k)) out.set(k, { dimension: k, count: 0, numericCount: 0, sum: 0, min: null, max: null });
      const slot = out.get(k);
      slot.count++;
      if (op === 'count') return;
      const raw = r[metric];
      if (raw == null || String(raw).trim() === '' || !Number.isFinite(Number(raw))) { invalid.push(i + 1); return; }
      const n = Number(raw); slot.numericCount++; slot.sum += n;
      if (!Number.isFinite(slot.sum)) throw Error('集計値が数値の範囲を超えました。元データを確認してください');
      slot.min = slot.min == null ? n : Math.min(slot.min, n);
      slot.max = slot.max == null ? n : Math.max(slot.max, n);
    });
    const groups = [...out.values()].map(g => ({ dimension: g.dimension, count: g.count, value: op === 'count' ? g.count : op === 'sum' ? g.sum : op === 'average' ? (g.numericCount ? g.sum / g.numericCount : null) : g[op] }));
    return { dimension, metric: op === 'count' ? null : metric, operation: op, groups, skippedNonNumericRows: invalid, totalRows: rows.length };
  }
  function permissionAudit(source) {
    if (!source || typeof source !== 'object') throw Error('権限設定JSONが必要です');
    const rules = Array.isArray(source) ? source : (source.rights || source.rules || []);
    if (!Array.isArray(rules)) throw Error('rights / rules 配列を解釈できません');
    const matrix = rules.map((r, i) => {
      if (!r || typeof r !== 'object' || Array.isArray(r)) throw Error('権限ルールの形式が不正です: ' + (i + 1));
      return ({
      order: i + 1,
      subject: r.entity && (r.entity.code || r.entity.type) || r.subject || '(不明)',
      entityType: r.entity && r.entity.type || '',
      condition: r.filterCond || r.condition || '',
      field: r.field || '',
      view: Boolean(r.viewRecord || r.view || r.read),
      add: Boolean(r.addRecord || r.add),
      edit: Boolean(r.editRecord || r.edit),
      delete: Boolean(r.deleteRecord || r.delete),
      raw: r
    });
    });
    return { ruleCount: matrix.length, matrix, warnings: ['規則の優先順位、ユーザー所属やレコード条件の実効権限は評価しません。定義の見える化専用です。'], permissionsModified: false };
  }
  const escapeHTML = value => String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[ch]);
  function reportHTML(source, selected, title) {
    const rows = dataRows(source);
    if (!rows.length) throw Error('帳票に出力するデータがありません');
    if (rows.length > 5000) throw Error('印刷可能な上限は5,000件です。対象を分割してください');
    const columns = selected && selected.length ? selected : Object.keys(rows[0]).filter(k => typeof rows[0][k] !== 'object');
    if (!columns.length || columns.length > 50 || columns.some(c => typeof c !== 'string' || !c || c.length > 128)) throw Error('印刷する列は1～50個で指定してください');
    const head = columns.map(c => '<th scope="col">' + escapeHTML(c) + '</th>').join('');
    const body = rows.map(row => '<tr>' + columns.map(c => '<td>' + escapeHTML(row[c] == null ? '' : row[c]) + '</td>').join('') + '</tr>').join('');
    return '<h2>' + escapeHTML(title || 'ResoArc 帳票') + '</h2><p>' + rows.length + ' 件</p><table class="print-table"><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table>';
  }
  return { parseDelimited, dataRows, loadText, bulkPreview, duplicateGroups, lookupAudit, aggregate, permissionAudit, reportHTML, escapeHTML };
});