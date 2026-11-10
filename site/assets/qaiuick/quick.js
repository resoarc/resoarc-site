/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *
 * qAIUIck Quick API. Human-facing code is intentionally tiny; the plumbing
 * for seed-once, persistence, CRUD, and redraw lives here.
 *
 * Existing createApp() and createStore() remain available for advanced use.
 */
import { createApp } from './qaiuick.js';

const RESERVED = new Set(['items', 'error', 'count', 'empty']);
const copy = value => JSON.parse(JSON.stringify(value));
const validName = /^[A-Za-z0-9_.-]{1,100}$/;

function uid() {
  return globalThis.crypto?.randomUUID?.() ??
    `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * quickApp({
 *   key: 'my-demo', sample: [{id:'one',title:'例'}],
 *   data: { draft: '' },
 *   actions: { add() { this.$add({title:this.draft}); this.draft=''; } }
 * });
 *
 * Built-in q-action="remove" and q-action="reset" need no user code.
 * Only `items` persist. Drafts and computed values are intentionally ephemeral.
 */
export function quickApp({
  root = '#app', key, sample = [], data = {},
  computed = {}, actions = {}, persist = 'local', storage, onError,
} = {}) {
  if (!validName.test(key ?? '')) throw new Error('quickApp requires a safe, unique key');
  if (persist !== 'local' && persist !== 'memory') throw new Error('Use persist: "local" or "memory"');
  if (!Array.isArray(sample) || !sample.every(x => x && typeof x === 'object' && !Array.isArray(x))) {
    throw new Error('sample must be an array of records');
  }
  if (!data || typeof data !== 'object' || Array.isArray(data) ||
      !computed || typeof computed !== 'object' || Array.isArray(computed) ||
      !actions || typeof actions !== 'object' || Array.isArray(actions)) {
    throw new Error('Invalid quickApp configuration');
  }
  if (Object.keys(data).some(name => RESERVED.has(name) || name.startsWith('$'))) {
    throw new Error('Reserved quickApp data property');
  }
  for (const name of Object.keys(actions)) {
    if (name.startsWith('$') || ['__proto__', 'constructor', 'prototype'].includes(name)) {
      throw new Error('Unsafe quickApp action name');
    }
  }
  const provider = persist === 'memory' ? null : (storage ?? globalThis.localStorage);
  if (persist === 'local' && !provider) throw new Error('localStorage unavailable; choose persist: "memory"');
  const storeKey = `qaiuick:${key}:items`;
  const seeded = copy(sample);
  let items;
  if (provider) {
    const raw = provider.getItem(storeKey);
    items = raw === null ? copy(seeded) : JSON.parse(raw);
    if (!Array.isArray(items)) throw new Error(`Saved data is not a list: ${key}`);
    if (raw === null) provider.setItem(storeKey, JSON.stringify(items));
  } else {
    items = copy(seeded);
  }
  const state = { ...copy(data), items, error: '' };
  const write = () => { if (provider) provider.setItem(storeKey, JSON.stringify(state.items)); };

  // Helpers are not enumerable state; the runtime, not the application, owns them.
  Object.defineProperties(state, {
    $add: { value(record) {
      if (!record || typeof record !== 'object' || Array.isArray(record)) throw new Error('$add expects a record');
      const next = copy({ ...record, id: record.id || uid() });
      state.items.push(next);
      return next;
    } },
    $remove: { value(id) {
      state.items = state.items.filter(row => String(row.id) !== String(id));
    } },
    $update: { value(id, changes) {
      const item = state.items.find(row => String(row.id) === String(id));
      if (!item) return false;
      if (typeof changes === 'function') changes(item);
      else if (changes && typeof changes === 'object' && !Array.isArray(changes)) Object.assign(item, copy(changes));
      else throw new Error('$update expects an object or updater function');
      return true;
    } },
    $reset: { value() { state.items = copy(seeded); state.error = ''; } },
    $error: { value(message) { state.error = String(message); } },
    $clear: { value(name) {
      if (!Object.prototype.hasOwnProperty.call(data, name)) throw new Error('Unknown field for $clear');
      state[name] = copy(data[name]);
    } },
  });
  const builtins = {
    add() {
      if (!Object.prototype.hasOwnProperty.call(data, 'draft')) {
        throw new Error('Add requires data.draft, or provide your own add action');
      }
      const draft = this.draft;
      const row = typeof draft === 'string' ? { title: draft.trim() } : copy(draft);
      if (!row || typeof row !== 'object' || Array.isArray(row) ||
          !Object.values(row).some(value => String(value ?? '').trim())) {
        return this.$error('入力してから追加してください');
      }
      this.$add(row);
      this.$clear('draft');
      this.error = '';
    },
    remove(id) { this.$remove(id); this.error = ''; },
    reset() { this.$reset(); },
  };
  const handlers = { ...builtins, ...actions };
  const wrapped = Object.fromEntries(Object.entries(handlers).map(([name, handler]) => {
    if (typeof handler !== 'function') throw new Error(`Invalid action: ${name}`);
    return [name, async (_state, { arg, event }) => {
      await handler.call(state, arg, event);
      write();
    }];
  }));
  const derive = {
    count: s => s.items.length,
    empty: s => s.items.length === 0,
    ...computed,
  };
  // Compatibility: legacy core still owns DOM event dispatch and safe q-text.
  const app = createApp({
    root, state, actions: wrapped, computed: derive,
    onError(error) {
      state.error = error?.message ?? String(error);
      app.render();
      if (onError) onError(error);
      else console.error(error);
    },
  });
  return {
    state, render: app.render, destroy: app.destroy,
    refresh() { write(); app.render(); },
    reset() { state.$reset(); write(); app.render(); },
  };
}
