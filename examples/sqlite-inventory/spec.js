/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 *  This is the complete application specification.
 */
export const spec = {
  id: 'inventory-local-sqlite',
  version: 1,
  title: '在庫管理（ローカルSQLite）',
  description: 'ブラウザを閉じても、SQLiteファイルにデータが残ります。',
  storage: 'sqlite',
  fields: {
    name: { label: '品目名', required: true, unique: true, minLength: 2 },
    category: ['部品', '工具', '消耗品'],
    qty: { label: '在庫数', type: 'number', min: 0, integer: true },
  },
  ui: {
    columns: ['name', 'category', 'qty'],
    search: ['name', 'category'],
    detail: ['name', 'category', 'qty'],
  },
  sample: [
    { id: 'item-1', name: 'M3ボルト', category: '部品', qty: 48 },
    { id: 'item-2', name: 'USB-Cケーブル', category: '部品', qty: 8 },
    { id: 'item-3', name: '養生テープ', category: '消耗品', qty: 6 },
  ],
};
