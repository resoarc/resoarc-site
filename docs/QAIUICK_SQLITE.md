# qAIUIck v0.6: ローカルSQLite保存とデータ保全

**標準Pythonだけ**でローカルSQLiteサーバーを動かし、利用者の仕様は
`storage: 'sqlite'` の1行で保存先を切り替えます。
フォーム、CRUD、入力検証、検索、状態管理は従来通りフレームワークが担当します。

## 初めての起動（Windows/macOS/Linux）

1. `qaiuick-v0.6-beta-source.zip` を展開します。
2. 展開フォルダ `qAIUIck-v0.6-beta` で次を実行します。

```sh
python -m qaiuick_local.server --root . --db ../qaiuick-data.sqlite3 --port 8765
```

3. PCのブラウザで `http://127.0.0.1:8765/examples/sqlite-inventory/` を開きます。

Python 3.10以上が必要です。追加pipパッケージやSQLiteサーバーの導入は不要です。
データベースは**Web公開ディレクトリの外側**に置きます。
サーバーは `127.0.0.1` のみにバインドし、外部公開やLAN共有はしません。

## 最小アプリ

```js
import { defineApp } from './define.js';

defineApp({
  id: 'my-stock',
  version: 1,
  title: '在庫管理',
  storage: 'sqlite',           // 追加はここだけ
  fields: {
    name: '品目名*',
    qty: { label: '数量', type: 'number', integer: true, min: 0 },
  },
});
```

`storage: 'sqlite'` は**専用のローカルサーバーを起動した場合のみ利用可能**です。
公開中のResoArcの静的なWebツール上では動きません。
標準の `storage: 'local'` または `persist: 'local'` は従来通り動作します。
既存のv0.5のアプリは設定変更不要です。

## 何を守るか

- SQLiteにレコード単位で保存し、別のタブからの古い世代番号による上書きをHTTP 409で拒否
- 同じアプリIDの項目名、型、入力制約が変わったら、勝手に移行せずHTTP 409で拒否
- 登録後に全部削除しても、初期データが自動で復活しない
- 64KB/レコード、2000件/アプリ、要求本文3MBの上限
- Origin、Host、セッション用トークンを検査。CORSを許可しない
- SQLiteファイルは静的配信対象から除外し、サーバーはループバック限定
- サーバー側でも型、数値範囲、一意性、必須を検証

これは**単独PCでのプロトタイプ・小規模ツール用**です。
認証・LANアクセス・複数ユーザーの同時編集・TLS・権限管理は未対応です。
インターネットに公開しないでください。

## バックアップ

実行例（サーバー稼働中でもSQLiteオンラインバックアップAPIで整合したコピーを作成）：

```sh
python -m qaiuick_local.cli backup --db ../qaiuick-data.sqlite3 --output ../backups/stock-20261110.sqlite3
python -m qaiuick_local.cli integrity --db ../backups/stock-20261110.sqlite3
```

既存ファイルへの上書きは拒否します。
復元も**既存DBをその場で上書きせず、新しいDBへ**行います。

```sh
python -m qaiuick_local.cli restore --source ../backups/stock-20261110.sqlite3 --output ../restored-data.sqlite3
```

内容を確認してからサーバーを停止し、`--db` を復元先の新しいファイルに切り替えます。
データの可搬性向けにJSONの出力・新DBへの取り込みにも対応します。

```sh
python -m qaiuick_local.cli export --db ../qaiuick-data.sqlite3 --app inventory-local-sqlite --output ../stock.json
python -m qaiuick_local.cli import --source ../stock.json --output ../imported.sqlite3
```

JSONエクスポートにはデータそのものが含まれるため、公開しないでください。

## 仕様の互換性確認

新仕様のJSONスナップショットを作ります。

```sh
node tools/qaiuick_spec.mjs snapshot examples/sqlite-inventory/spec.js ../candidate.json
python -m qaiuick_local.cli check-schema --db ../qaiuick-data.sqlite3 --spec ../candidate.json
```

返り値は `NEW_APP`、`COMPATIBLE`、`BLOCKED`。
`BLOCKED` は終了コード3です。DBの項目定義が異なる場合、勝手に移行せず
バックアップ取得・差分レビューを促します。
`version` だけが進み、保存形式に影響しないUI変更なら継続できます。

### 制限

- 任意のSQL実行APIではなく、定義済みのレコードCRUDのみを扱います。
- 現段階の更新はアプリの全レコードを一トランザクションで保存します。大量データ用の差分更新は今後の課題です。
- データ移行は**自動実行しません**。互換性判定と安全停止までをv0.6の範囲とします。
- SQLiteによるローカル保存はバックアップを不要にするものではありません。
- 完全な既存DB連携、クラウド・100ユーザー向けSaaS機能は後続版の対象です。
