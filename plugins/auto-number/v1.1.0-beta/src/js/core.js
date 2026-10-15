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