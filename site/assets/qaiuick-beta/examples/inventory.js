/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { quickApp } from '/assets/qaiuick/quick.js';

quickApp({
  key: 'resoarc-qaiuick-sample-inventory-v1',
  sample: [
    { id:'stock-1', name:'M3ボルト', category:'部品', qty:48, min:20 },
    { id:'stock-2', name:'USB-Cケーブル', category:'部品', qty:8, min:12 },
    { id:'stock-3', name:'養生テープ', category:'消耗品', qty:6, min:5 },
    { id:'stock-4', name:'六角レンチ', category:'工具', qty:3, min:4 },
    { id:'stock-5', name:'小型ケース', category:'部品', qty:25, min:10 },
  ],
  data: { draft:{name:'',qty:'1',min:'5',category:'部品'} },
  computed: {
    totalUnits: s => s.items.reduce((n, r) => n + Number(r.qty), 0),
    lowStock: s => s.items.filter(r => Number(r.qty) < Number(r.min)).length,
  },
  actions: {
    add() {
      const { name, category } = this.draft;
      const qty = Number(this.draft.qty), min = Number(this.draft.min);
      if (!name.trim() || !Number.isInteger(qty) || !Number.isInteger(min) ||
          qty < 0 || min < 0 || qty > 99999 || min > 99999)
        return this.$error('品目名と0〜99999の整数を指定してください');
      this.$add({ name:name.trim(), category, qty, min });
      this.$clear('draft');
      this.error = '';
    },
    restock(id) {
      this.$update(id, row => { row.qty = Math.min(99999, Number(row.qty) + 10); });
    },
  },
});
