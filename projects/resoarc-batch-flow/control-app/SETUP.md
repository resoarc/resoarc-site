# ResoArc Batch Center / Clock セットアップ（開発版）

## 1. kintoneの管理アプリを作成

**専用アプリの作成を自動化する方法（テストテナント専用）**: リポジトリ直下で `npm run build:installer` を実行し、生成された `release/resoarc-clock-bootstrap-v0.3.1.js` の内容を、管理者本人がログインしたテスト用kintoneのブラウザー開発者コンソールで実行します。画面の確認ダイアログで許可した後、新規アプリのみ作成・フィールド設定・レイアウト設定・デプロイ要求を行います。既存アプリは変更せず、APIトークンやパスワードを入力しません。作成された新アプリIDを控え、プラグインの読み込み・追加、トークン発行は別途実施してください。APIの模擬テストは済みですが実テナントではまだ未確認です。

**手動作成する方法**: 以下のフィールドを設定します。

名前例「ResoArc バッチ管理」。control-app/fields.json のフィールドコードと種類を管理アプリに設定してください。

- BatchName：バッチ名（1行文字列）
- BatchEnabled：停止／有効（ドロップダウン、初期値停止）
- DailyTime：毎日モードの日本時間（時刻）
- ScheduleType：毎日／間隔／一回（ドロップダウン、初期値毎日）
- IntervalMinutes：1～10080分（数値）
- OneTimeAt：一回実行日時（日時）
- NextRunAt：次回実行予定（日時）
- RunState：待機／実行中／正常終了／要確認（ドロップダウン、初期値待機）
- RunToken、LastStartedAt、LastFinishedAt、LastResult、RunHistory：実行権・実行結果・履歴
- Steps：TaskType、TargetApp、Query、FieldsJSONを含むサブテーブル

追加のScheduleType、IntervalMinutes、OneTimeAtが存在しない従来の管理アプリは「毎日」モードとして動作します。

## 2. プラグインを設定

管理アプリに「ResoArc Batch Center v0.2.0」を追加し、アプリ設定を更新します。
自動実行を「停止」にした状態でレコードを作り、スケジュールとStepsに実行順を設定します。保存後にNextRunAtが設定されたことを確認します。
詳細画面の「処理をテスト（変更なし）」で対象件数・実行順を確認し、テスト用アプリで手動実行を検証します。
レコードの編集保存でスケジュール時刻が再計算されます。

## 3. 完全無人実行

worker/CLOCK.mdに沿って、利用者自身のCloudflareアカウントに1個の毎分Cronを導入します。
Workerは初期状態でRA_CLOCK_ENABLED=false、RA_ALLOW_WRITES=falseです。kintone接続を一切しないところから始めます。
接続情報をSecretsに保存してから、まずClockだけ有効化して読み取り試験し、業務データの書き込みはテストとバックアップの後に許可してください。

## 4. 事故防止

- 一回実行は正常終了すると自動実行を停止にします。
- タスク失敗は「要確認」で停止します。成功済みステップの変更は自動ロールバックできません。
- Workerが強制終了した場合は「実行中」が残ることがあります。二重登録防止のため自動復旧させません。
- Cloudflare無料枠への安全策で1周期最大2バッチを処理し、残りは次のCronへ繰り越します。
- APIトークンはCloudflare Secretsで利用者自身が管理します。ResoArcへ送信しません。
- 本番kintoneとの実環境E2E試験は未実施です。公開前に書き込み権限・障害対応・バックアップの実地試験が必要です。
