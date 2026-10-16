# ResoArc Batch Flow + ResoArc Clock v0.3.5（検証版）

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
- **kintone管理アプリの新規作成補助**: `npm run build:installer` で `release/resoarc-clock-bootstrap-v0.3.5.js` を生成し、管理者本人がログインしたテストテナントの開発者ツールで実行。既存アプリは変更せず、実行前の確認が必要。プラグインのシステム管理へのアップロードは別作業。
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

コード・モックAPIを使ったNode.js試験とWranglerのビルド検証を実施しています。**Cloudflareへの停止状態での実デプロイ・Cron発火、管理アプリと4タスク手動バッチのkintone実テナントE2Eは確認済みです。ただし、Cloudflare Cronからkintoneまでの無人**読み取り**E2Eは成功済みですが、無人**書き込み**E2Eは未完了のため、正式リリース前の検証版です。** WorkerのCronからブラウザ用プラグインJavaScriptを直接動かすことはできません。実行可能な処理は上記の共通アクションです。

## 制約

kintone側のレコード更新はバッチ全体のトランザクションではありません。先行タスクが成功して後続が失敗した場合、先行変更は戻りません。日時の厳密な秒精度は保証しません。カスタムドメイン、ゲストスペース、任意のサーバー側JavaScriptの実行は現在非対応です。

## v0.3.2 安全性の追加（検証版）

- Workerの定期起動は `RA_CLOCK_ENABLED=true` を明示した場合のみ有効です。設定を省略した場合、定期処理は動作しません。
- 前回失敗で `要確認` のバッチは手動再実行できません。転記・登録の二重実行がないことを確認後、管理アプリで実行状態を `待機` に戻します。
- 一回実行済みのバッチも同様に、意図的な再実行操作が必要です。テスト実行（書き込みなし）は引き続き可能です。
- `release/RELEASE-0.3.2.md` に変更点と正式リリース前の未確認項目を記載しています。

## MR kintone高速テストとの連携

実環境向け検証は [MR統合テスト手順](docs/MR-KINTONE-ACCEPTANCE.md) を参照してください。`npm run test:mr-readiness` で、Mole Remoteのプラグイン静的検査・kintone API疎通・専用Edgeログイン・Batch Center管理アプリの設定状態を**読み取り専用**で診断できます。自動採番専用テストアプリ48はBatch Centerの書き込み先として使用しません。

管理アプリ未作成時は `center_app_not_ready` と表示し、リリース合格と誤認しないようにします。GitHub CIは環境に認証情報がないため、MR連携スクリプトの単体テストだけを実行します。

## v0.3.3 API通信削減

**kintoneへの常時毎分ポーリングを廃止**し、Cloudflare KVで次回実行時刻を覚える適応型モードを追加しました。予定がない場合は10分に1回の確認だけ行います。

1日1,440回のCron起動に対して、予定がない場合のkintone照会は144回（**90%削減**）、KV読取りは1,440回、KV書き込みは144回です。毎分の実行が必要なバッチではkintoneの毎分照会が発生します。KV書き込みは2分の間隔を守り、無料枠を節約します。

`RA_POLL_MODE=adaptive` を選ぶ場合、`RA_CLOCK_STATE` のCloudflare KVバインディングが必要です。KVが壊れている／未設定の場合は無断で毎分ポーリングに戻さず停止します。従来動作は `RA_POLL_MODE=minute` で明示可能です。セットアップは [worker/CLOCK.md](worker/CLOCK.md) を参照してください。

kintoneへの設定反映は最大約10分＋KVの伝播遅延がかかる場合があります。秒単位の正確な実行や、予定変更直後の即時反映は保証していません。

## v0.3.4 kintone検証テナントとの照合

- 空欄の実行予定日時を持つレコードを検索時点で除外し、適応型・毎分型の双方で実行予定の取りこぼしを防ぐテストを追加。
- アプリ設定の反映APIはkintone公式仕様に従いPOSTを使用。実kintone検証で成功したメソッドを回帰テストで確認。
- Mole Remoteの専用kintoneテストテナントで認証・読み取りAPI・専用Edgeの利用可否を確認。
- ResoArc Clock専用の検証管理アプリ（ID 50）が既に存在し、プラグイン有効・フィールド不足なし。重複作成しない設計。
- 実テナントで日時空欄除外の検索クエリが正常に受け付けられることを確認。
- 続いて専用QAデータアプリに対し、取得・更新・転記・登録の4ステップを書き込み実行し、結果を検証。作成したテストレコード3件は照合後に削除して残件0を確認。異常停止と再実行抑止も実画面で合格。
- [実kintoneステージングE2Eレポート](docs/REAL-KINTONE-STAGING-E2E-20261017.md) に試験範囲、結果、未検証条件を記載。Cloudflare Clockの無人実行E2Eは引き続き未実施。
- 変更点と未検証範囲は release/RELEASE-0.3.4.md に記載。kintone実データの書き込みE2Eが未了なので正式リリースではありません。

## v0.3.5 Live read-only E2E

- kintoneの専用バッチ管理テストアプリへ、最小権限（閲覧のみ）のAPIトークンを発行。
- 認証情報はPC内からCloudflare Secretsに直接登録。ソースや配布キットには保存しません。
- 実Cloudflare Cronからkintone予定取得、KVキャッシュ更新、参照のみのバッチ実行（DRY RUN）まで**実機で確認済み**。
- テストレコードは停止し、現在のKVは次回予定なし・10分再同期間隔に戻っています。
- Cloudflare側は RA_ALLOW_WRITES=false を維持しています。書込み系バッチと復旧動作の実機試験は未実施であり、**正式リリース前の検証版**です。
- 詳細は release/RELEASE-0.3.5.md に記録しています。

## Cloudflare再接続の安全チェック

`npm run cloud:preflight` はWorker設定が書込み禁止か検査した上で、Cloudflareのログイン状態だけでなく**対象Workerのデプロイ一覧を実際に取得できるか**まで確認します。結果が `ready=false` のときは、クラウド書き込み試験を進めません。

Cloudflare Cron経由の読み取り専用実環境E2Eは合格。書き込み自動実行の検証は認証で中断し、検証用レコードは停止・削除済みです。詳細は [Cloudflare × kintone ステージング検証](docs/CLOUDFLARE-KINTONE-STAGING-20261017.md) を参照してください。
