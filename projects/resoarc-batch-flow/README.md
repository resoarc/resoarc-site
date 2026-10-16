# ResoArc Batch Flow + ResoArc Clock v0.3.1（検証版）

kintoneアプリ内のバッチ管理画面で処理を定義し、任意の複数タスクを順次実行する無料／オープンソースのツールです。MIT License。

## 動作モード

- **手動実行:** kintoneのレコード詳細画面のボタンで、確認後に順次実行。外部実行環境不要。
- **完全無人実行:** 利用者自身のCloudflare Workersに1個の毎分Cronを設定。設定したバッチ管理アプリから予定日時を確認し、期限到来分だけを実行。プラグイン設定の変更ごとにCronを再デプロイする必要はありません。
- **従来方式:** バッチ定義JSONをCloudflareに登録する旧方式も互換性維持。新規導入にはResoArc Clock方式を推奨。

対応するスケジュールは「毎日（日本時間HH:mm）」「1～10080分間隔」「日時指定の一回実行」です。一回実行の正常終了後はそのバッチを停止します。Cron自体の起動は遅延する場合があります。

## 対応タスク

1. レコード取得（条件指定、最大100件）
2. レコード更新（取得対象への固定値設定）
3. 別アプリへ転記（フィールドコードでマッピング）
4. レコード追加（固定値で1件作成）

1バッチ最大20ステップ。異なるアプリのAPIトークンは利用者自身のCloudflare Secretsに保存します。ResoArc運営者へ渡す必要はありません。

## kintone管理アプリ

1レコードが1つのバッチに対応し、処理手順はStepsサブテーブルへ上から順に登録します。実行状態・次回予定日時・最後の実行結果・履歴は管理アプリに保持されます。

- 設計: [control-app/README.md](control-app/README.md)
- 初期設定: [control-app/SETUP.md](control-app/SETUP.md)
- **kintone管理アプリの新規作成補助**: `npm run build:installer` で `release/resoarc-clock-bootstrap-v0.3.1.js` を生成し、管理者本人がログインしたテストテナントの開発者ツールで実行。既存アプリは変更せず、実行前の確認が必要。プラグインのシステム管理へのアップロードは別作業。
- 無人実行・Cloudflare: [worker/CLOCK.md](worker/CLOCK.md)
- 設定テンプレート: [worker/center-wrangler.example.jsonc](worker/center-wrangler.example.jsonc)

## 初期状態と安全策

- Workerの初期状態は **RA_CLOCK_ENABLED=false**、**RA_ALLOW_WRITES=false**。そのままデプロイしてもkintoneへ通信しません。
- **Worker無料枠を想定し、1周期最大2バッチ** に抑制。1バッチの20ステップと管理レコードへの2回の書き込みから、最悪で1+2×22=45のサブリクエストに収まる設計です（Workers Freeの上限50）。
- kintoneのレコードrevisionを使って、同時実行の実行権競合を判定します。
- 一部のステップが失敗した場合は「要確認」に停止し、自動で再実行しません。登録・転記の重複を防ぐため、結果不明の処理も自動リトライしません。
- Workerが強制停止した場合は「実行中」が残ることがあります。業務データを確認してから手動復旧が必要です。
- 初期の書き込み試験前には必ずバックアップを取得し、最小権限トークンとテスト用アプリで確認してください。

## 検証

    npm test
    cd worker
    npx wrangler deploy --dry-run --config center-wrangler.example.jsonc

コード・モックAPIを使ったNode.js試験とWranglerのビルド検証を実施しています。**kintone実テナントとの結合試験およびCloudflareへの実デプロイは未実施で、正式リリース前の検証版です。** WorkerのCronからブラウザ用プラグインJavaScriptを直接動かすことはできません。実行可能な処理は上記の共通アクションです。

## 制約

kintone側のレコード更新はバッチ全体のトランザクションではありません。先行タスクが成功して後続が失敗した場合、先行変更は戻りません。日時の厳密な秒精度は保証しません。カスタムドメイン、ゲストスペース、任意のサーバー側JavaScriptの実行は現在非対応です。
