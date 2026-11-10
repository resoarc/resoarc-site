/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  The one source of truth for the application specification.
 */
export const spec = {
  id: 'resoarc-qaiuick-spec-inventory',
  version: 2,
  title: '在庫管理・仕様駆動版',
  description: '部品を登録し、補充ライン以下の在庫を見つけます。',
  fields: {
    name: { label: '品目名', required: true, unique: true, minLength: 2, maxLength: 60, hint: '重複した品目名は登録できません' },
    category: { label: '分類', options: ['部品', '工具', '消耗品'] },
    qty: { label: '在庫数', type: 'number', min: 0, integer: true, default: 0 },
    limit: { label: '補充ライン', type: 'number', min: 0, integer: true, default: 5 },
  },
  ui: {
    columns: ['name', 'category', 'qty', 'limit'],
    search: ['name', 'category'],
    sections: [
      { title: '品目情報', fields: ['name', 'category'] },
      { title: '在庫と補充', fields: ['qty', 'limit'] },
    ],
    detail: ['name', 'category', 'qty', 'limit'],
  },
  metrics: {
    low: { label: '補充対象', calc: rows => rows.filter(r => r.qty < r.limit).length },
  },
  actions: {
    restock: {
      label: '+10', description: '選択品目の在庫を10増やす',
      run: ({ record, update }) => update(record.id, { qty: record.qty + 10 }),
    },
  },
  sample: [
    { id: 's1', name: 'M3ボルト', category: '部品', qty: 48, limit: 20 },
    { id: 's2', name: 'USB-Cケーブル', category: '部品', qty: 8, limit: 12 },
    { id: 's3', name: '養生テープ', category: '消耗品', qty: 6, limit: 5 },
  ],
};
