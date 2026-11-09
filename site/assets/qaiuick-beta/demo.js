import { createApp } from '/assets/qaiuick/qaiuick.js';
import { createStore } from '/assets/qaiuick/store.js';

const store = createStore({ namespace: 'resoarc-qaiuick-public-beta' }); // Browser localStorage
const state = { draft: '', tasks: [], error: '' };

const app = createApp({
  root: '#app',
  state,
  computed: {                      // Display values: no manual sync needed
    count: (s) => s.tasks.length,
    empty: (s) => s.tasks.length === 0,
  },
  actions: {
    async add(s) {
      const title = s.draft.trim();
      if (!title) { s.error = 'メモを入力してください'; return; }
      await store.save({ title });
      s.draft = '';
      s.error = '';
      s.tasks = await store.list();
    },
    async remove(s, { arg }) {
      await store.remove(arg);
      s.tasks = await store.list();
    },
  },
  onError(error) { state.error = error.message; app.render(); },
});

try { state.tasks = await store.list(); app.render(); }
catch (error) { state.error = `保存領域を使用できません: ${error.message}`; app.render(); }
