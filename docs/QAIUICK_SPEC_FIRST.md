# qAIUIck Spec-first API（実験版）

**考え方：実装仕様を読むだけでアプリがわかり、共通動作はフレームワークに任せる。**

## 最小のアプリ

```javascript
import { defineApp } from '/assets/qaiuick/define.js';

defineApp({
  id: 'my-inventory',
  version: 1,
  title: '在庫管理',
  fields: {
    name: '品目名*',                               // 必須テキスト
    qty: { label: '在庫数', type: 'number', min: 0 },
  },
  ui: { search: ['name'] },                      // 検索対象
});
```

HTMLは `<div id="app"></div>` と qAIUIck Core/Spec CSSの読み込み、
上記JavaScriptのモジュール読み込みのみ。フォーム、一覧、検索、追加・編集・削除、
保存、初期化、入力検証、レスポンシブ表示、仕様JSON表示は自動生成。

## コードを読む順序

1. `id`, `version`, `title`, `description`: 何のアプリで、どの仕様版か
2. `fields`: 項目の名前、型、必須、選択肢、範囲、デフォルト値
3. `ui`: 表示列と検索対象
4. `metrics`: 画面に表示する集計指標（関数で自由に拡張）
5. `actions`: 独自の操作。ラベル・説明・処理を隣に記述
6. `sample`: 最初のアクセス時だけ投入するデモレコード

未指定項目は共通の安全な既定値を使用。未対応の型は起動時にエラーになります。
インターフェイスの追加は `slots.beforeForm` と `slots.afterList` で
安全なDOM Nodeを返す関数として挿入できます。既存の`quickApp`/`createApp`、
手書きHTML・CSS・JSも引き続き利用できます。

### 保存について

`persist: 'local'` が既定（ブラウザのlocalStorage）。
`persist: 'memory'` で一時記憶。複数人・権限・HTTPS・SQLite・既存DBとの連携には
別途認証付きバックエンドと既存の上位APIを使います。
個人情報・業務機密を公開デモに保存しないこと。

スキーマ変更による破壊的なデータ移行は自動実施しません。
実データがある場合は、個別にバックアップ・マイグレーションを設計します。

## 変更差分の見方（AIレビュー）

仕様ファイルには `export const spec = { ... }` で仕様を書きます。
ビルド不要で、CLIだけでスナップショットを生成できます。

```sh
node tools/qaiuick_spec.mjs snapshot site/assets/qaiuick-spec/inventory.spec.js baseline.json
node tools/qaiuick_spec.mjs diff baseline.json candidate.json
```

CLIは項目・表示順・検索条件・初期データ・独自操作の関数本体を比較し、
`~ fields.qty.min: 0 => 5` のように差分の場所を表示します。
変更後のコードを読まなくても、どこに影響したかを確認するための補助です。

画面の「実装仕様とAIの変更差分を確認」にも、同じJSONと
配信された基準仕様からの差分が表示されます。変更がない場合はその旨を明示。
基準JSONが取得できない場合は検査不能と表示します。

**注意：** この比較はコードレビュー・実動作テストの代わりにはなりません。
仕様に含まれない外部サービスやフレームワーク内部の変更は別途検査が必要です。

## AIに渡す依頼フォーマット

> `<app>.spec.js` を変更してください。既存の `id` と保存済みデータを維持し、
> 変更する項目と操作のみ更新し、`version` を上げてください。
> CLIで基準仕様と比較し、差分とテスト結果を報告してください。
> 既存データの移行が必要なら無断実行せず別途検討してください。

## 既存API

- **Spec-first**: 項目宣言からアプリを自動生成。最も記述量が少ない
- **Quick API**: HTMLを自分で書き、状態管理・保存・更新を自動化
- **Core API**: 画面と処理を自由に制御。特殊なUI・API連携向け

複雑な案件も「簡単に書いた結果、後から変更不能」にならない構造を維持します。
