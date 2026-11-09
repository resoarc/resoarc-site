/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { createApp } from '/assets/qaiuick/qaiuick.js';
import { createStore } from '/assets/qaiuick/store.js';
import { seedOnce, resetSamples } from '/assets/qaiuick-beta/examples/sample-data.js';
const namespace = 'resoarc-qaiuick-public-beta';
const store = createStore({ namespace });
const examples = [
  { id:'memo-1', title:'qAIUIckのコードを読んでみる' },
  { id:'memo-2', title:'HTML・CSS・JSを切り替えて確認する' },
  { id:'memo-3', title:'メモを追加して保存を試す' },
];
const state = { draft: '', tasks: [], error: '' };
const app = createApp({
  root: '#app', state,
  computed: {
    count: s => s.tasks.length,
    empty: s => s.tasks.length === 0,
  },
  actions: {
    async add(s) {
      const title = s.draft.trim();
      if (!title) { s.error = 'メモを入力してください'; return; }
      await store.save({ title });
      s.draft = ''; s.error = ''; s.tasks = await store.list();
    },
    async remove(s, { arg }) {
      await store.remove(arg); s.tasks = await store.list(); s.error = '';
    },
    async reset(s) {
      s.tasks = await resetSamples(store, examples); s.draft = ''; s.error = '';
    },
  },
  onError(error) { state.error = error.message; app.render(); },
});
try { state.tasks = await seedOnce(store, namespace, examples); app.render(); }
catch (error) { state.error = `保存領域を使用できません: ${error.message}`; app.render(); }
