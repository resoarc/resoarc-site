/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { quickApp } from '/assets/qaiuick/quick.js';

const yen = value => Number(value).toLocaleString('ja-JP') + ' 円';
quickApp({
  key: 'resoarc-qaiuick-sample-budget-v1',
  sample: [
    {id:'expense-1',category:'食費',amount:980,note:'お昼の定食'},
    {id:'expense-2',category:'交通',amount:760,note:'電車'},
    {id:'expense-3',category:'日用品',amount:1480,note:'洗剤'},
    {id:'expense-4',category:'食費',amount:2250,note:'食材の買い物'},
    {id:'expense-5',category:'趣味',amount:3300,note:'画材'},
  ],
  data: { draft:{category:'食費',amount:'',note:''} },
  computed: {
    total: s => yen(s.items.reduce((n, r) => n + Number(r.amount), 0)),
    foodTotal: s => yen(s.items.filter(r => r.category === '食費')
      .reduce((n, r) => n + Number(r.amount), 0)),
  },
  actions: {
    add() {
      const { category, note } = this.draft;
      const amount = Number(this.draft.amount);
      if (!note.trim() || !Number.isSafeInteger(amount) || amount < 1 || amount > 10000000)
        return this.$error('用途と1〜10000000円の整数を入力してください');
      this.$add({ category, amount, note:note.trim() });
      this.$clear('draft');
      this.error = '';
    },
  },
});
