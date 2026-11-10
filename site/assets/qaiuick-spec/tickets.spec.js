/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  The one source of truth for the application specification.
 */
export const spec = {
  id: 'resoarc-qaiuick-spec-tickets',
  version: 1,
  title: '問い合わせ管理・仕様駆動版',
  description: '受付、対応中、完了の流れを小さな仕様で定義します。',
  fields: {
    title: '問い合わせ内容*',
    owner: '担当者*',
    status: { label: '対応状況', options: ['未対応', '対応中', '完了'] },
  },
  ui: { columns: ['title', 'owner', 'status'], search: ['title', 'owner'] },
  metrics: {
    open: { label: '未完了', calc: rows => rows.filter(r => r.status !== '完了').length },
  },
  actions: {
    advance: {
      label: '次へ', description: '未対応 → 対応中 → 完了',
      run: ({ record, update }) => {
        const stages = ['未対応', '対応中', '完了'];
        update(record.id, { status: stages[(stages.indexOf(record.status) + 1) % 3] });
      },
    },
  },
  sample: [
    { id: 't1', title: 'ログイン方法の確認', owner: '田中', status: '未対応' },
    { id: 't2', title: '集計表示について', owner: '山本', status: '対応中' },
    { id: 't3', title: 'ファイル保存方法', owner: '佐々木', status: '完了' },
  ],
};
