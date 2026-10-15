/*
 * ResoArc Auto Number v1.0.0
 * SPDX-License-Identifier: MIT
 * Pure numbering logic. Exportable for tests, no browser side effects.
 */
(function (global, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (global) global.ResoArcAutoNumber = api;
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const MAX_PREFIX = 20;
  function validConfig(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const field = String(raw.field || '').trim();
    const prefix = String(raw.prefix || '');
    const width = Number(raw.width);
    const start = String(raw.start || '1');
    if (!field || field.length > 128 || !/^[A-Za-z0-9_-]*$/.test(prefix) || prefix.length > MAX_PREFIX
      || !Number.isInteger(width) || width < 3 || width > 12
      || !/^[1-9][0-9]{0,8}$/.test(start)) return null;
    return { field, prefix, width, start };
  }
  function makeNumber(recordId, raw) {
    const config = validConfig(raw);
    const id = String(recordId);
    if (!config || !/^[1-9][0-9]*$/.test(id)) throw new Error('設定またはレコードIDが不正です。');
    const value = BigInt(id) + BigInt(config.start) - 1n;
    const numeric = value.toString().padStart(config.width, '0');
    const output = config.prefix + numeric;
    if (output.length > 64) throw new Error('採番文字列が64文字を超えています。');
    return output;
  }
  return { validConfig, makeNumber };
});