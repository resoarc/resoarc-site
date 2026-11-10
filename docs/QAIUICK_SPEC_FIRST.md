# qAIUIck Spec-first API v0.5

**設計思想：** 「業務仕様は短い宣言で、画面・入力検証・CRUD・保存・影響分析はフレームワークに」。

## これだけでアプリになる

```js
import { defineApp } from './define.js';

defineApp({
  id: 'sample-stock',
  version: 1,
  title: '在庫管理',
  fields: {
    name: { label: '品目名', required: true, unique: true, minLength: 2 },
    qty: { label: '数量', type: 'number', min: 0, integer: true },
  },
  ui: { search: ['name'] },
});
```

HTMLに `<div id="app"></div>` とスタイル、上記モジュールだけを配置します。フォーム・一覧・検索・追加・編集・削除・ローカル保存・スマホ用レイアウトは自動生成されます。

## 仕様の読み方

| 宣言 | 意味 |
| --- | --- |
| `id`, `version`, `title` | アプリの識別子・仕様版・画面タイトル |
| `fields` | 項目名、型、必須、数値範囲、重複禁止、文字数、ヒント |
| `ui.columns` | 一覧に表示する項目の順番 |
| `ui.search` | 検索対象の項目 |
| `ui.sections` | フォームをグループに分け、項目順を指定 |
| `ui.detail` | 「詳細」ボタンで表示する項目 |
| `metrics` | 集計値を作る関数 |
| `actions` | 標準CRUDでは表せない業務操作 |
| `sample` | 初回アクセス時だけ投入する例示データ |

例えば、入力フォームを見やすく分ける場合は次のように追加します。

```js
ui: {
  columns: ['name', 'category', 'qty'],
  search: ['name'],
  sections: [
    { title: '品目', fields: ['name', 'category'] },
    { title: '数量', fields: ['qty'] },
  ],
  detail: ['name', 'category', 'qty'],
}
```

`ui.sections`に列挙した項目に重複・漏れがある場合は、起動時に検出します。省略した場合は、全項目を一つの入力セクションに表示します。

入力ルールは `required`, `minLength`, `maxLength`, `min`, `max`, `integer`, `unique` を組み合わせます。重複チェックは入力時の記録に対して動作し、既存レコードの編集時は自分自身を除外します。ブラウザの入力属性だけに依存せず、保存時も同じ規則で検証します。ただし、複数ユーザーや外部APIに対するサーバー側検証の代用ではありません。

## AI変更の影響がすぐわかる

仕様を **同じIDのまま改訂** したら、`version` を更新し、スナップショットと基準版を比較できます。

```sh
node tools/qaiuick_spec.mjs snapshot examples/spec-inventory/spec.js current.json
node tools/qaiuick_spec.mjs diff examples/spec-inventory/baseline.json current.json
```

例：

```text
+ fields.name.unique  => true
+ ui.sections => [ ... ]
~ version 1 => 2
IMPACT 入力フォーム・検証 | 追加・編集で必須・範囲・重複を確認 | 要確認
IMPACT フォーム配置 | スマホ・PCの項目順と表示を確認 | 低
DATA_REVIEW_REQUIRED
```

公開デモの「実装仕様とAIの変更差分を確認」でも、変更箇所・影響範囲・推奨試験を確認できます。これはルールベースの**確認漏れ防止**であり、AI変更の正しさを保証するものではありません。

スキーマ変更による自動データ移行・権限変更は行いません。保存済みデータの形式が変わる場合は、バックアップと手動レビューが必要です。

## 拡張の考え方

`actions` で任意の業務処理を定義できます。規定された `record`, `records`, `update`, `add`, `remove` を介して行い、毎回の保存・画面更新はフレームワークに任せます。見た目を独自化したい場合は `slots.beforeForm` と `slots.afterList` を使用します。

細かい画面を完全に手書きしたい場合は、従来の `quickApp()`、`createApp()` をそのまま利用できます。

`persist: 'local'` が既定（localStorage）、`persist: 'memory'` は再読み込みで消去。SQLiteや既存DB、複数ユーザー・認証・権限は本APIの範囲外で、適切なサーバー実装が必要です。

公開サンプルへ本物の個人情報や機密情報を入力しないでください。
