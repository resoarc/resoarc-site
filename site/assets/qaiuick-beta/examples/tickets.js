/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { quickApp } from '/assets/qaiuick/quick.js';

const stages = ['未対応', '対応中', '完了'];
quickApp({
  key: 'resoarc-qaiuick-sample-tickets-v1',
  sample: [
    {id:'ticket-1',title:'ログイン方法の確認',owner:'田中',status:'未対応'},
    {id:'ticket-2',title:'集計表の表示について',owner:'山本',status:'対応中'},
    {id:'ticket-3',title:'添付ファイルの保存方法',owner:'佐々木',status:'完了'},
    {id:'ticket-4',title:'モバイル画面の使い方',owner:'鈴木',status:'未対応'},
  ],
  data: { draft:{title:'',owner:''} },
  computed: {
    openCount: s => s.items.filter(r => r.status !== '完了').length,
    doneCount: s => s.items.filter(r => r.status === '完了').length,
  },
  actions: {
    add() {
      const { title, owner } = this.draft;
      if (!title.trim() || !owner.trim()) return this.$error('内容と担当者を入力してください');
      this.$add({ title:title.trim(), owner:owner.trim(), status:'未対応' });
      this.$clear('draft');
      this.error = '';
    },
    advance(id) {
      this.$update(id, row => {
        row.status = stages[(stages.indexOf(row.status) + 1) % stages.length];
      });
    },
  },
});
