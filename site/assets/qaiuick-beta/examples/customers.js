/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { quickApp } from '/assets/qaiuick/quick.js';

const matches = (row, query) => [row.name, row.company, row.region]
  .some(value => value.toLocaleLowerCase('ja-JP').includes(query));
quickApp({
  key: 'resoarc-qaiuick-sample-customers-v1',
  sample: [
    {id:'customer-1',name:'佐藤 葵',company:'星野商事',region:'東京'},
    {id:'customer-2',name:'田中 智',company:'浜風製作所',region:'広島'},
    {id:'customer-3',name:'鈴木 春',company:'星野商事',region:'大阪'},
    {id:'customer-4',name:'山田 陽',company:'青葉デザイン',region:'福岡'},
    {id:'customer-5',name:'高橋 凛',company:'山崎工業',region:'東京'},
  ],
  data: { query:'', draft:{name:'',company:'',region:''} },
  computed: {
    filtered: s => s.items.filter(r => matches(r, s.query.trim().toLocaleLowerCase('ja-JP'))),
    visibleCount: s => s.items.filter(r => matches(r, s.query.trim().toLocaleLowerCase('ja-JP'))).length,
    companyCount: s => new Set(s.items.map(r => r.company)).size,
    empty: s => !s.items.some(r => matches(r, s.query.trim().toLocaleLowerCase('ja-JP'))),
  },
  actions: {
    add() {
      const { name, company, region } = this.draft;
      if (![name,company,region].every(x => x.trim())) return this.$error('すべての項目を入力してください');
      this.$add({ name:name.trim(), company:company.trim(), region:region.trim() });
      this.$clear('draft');
      this.query = '';
      this.error = '';
    },
  },
});
