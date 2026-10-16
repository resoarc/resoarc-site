# ResoArc Batch Center 管理アプリ構成（試作版）

1つのkintone管理アプリを追加し、1レコードに1つのバッチを登録する方式です。

## フィールド

`fields.json` はkintoneフォーム構成の定義案です。管理アプリに登録する項目は以下です。

| フィールドコード | 内容 |
|---|---|
| BatchName | バッチ名 |
| BatchEnabled | 自動実行の有効／停止 |
| DailyTime | 日本時間の実行時刻 |
| ScheduleType / IntervalMinutes / OneTimeAt | 毎日／間隔／一回の切替、1～10080分間隔、日時指定（任意フィールド） |
| NextRunAt | 次回予定日時 |
| RunState | 待機／実行中／正常終了／要確認 |
| LastStartedAt / LastFinishedAt | 直近の開始・終了日時 |
| LastResult / RunHistory | 最新結果と履歴 |
| RunToken | 実行ロック識別子 |
| Steps | 処理順を表すサブテーブル |

サブテーブル「Steps」はTaskType、TargetApp、Query、FieldsJSONの4項目で構成します。

## 利用方法

1. 空のkintoneアプリを作り、fields.jsonの構成に従ってフィールドを作ります。
2. 専用のResoArc Batch Centerプラグインを管理アプリに追加します。
3. レコードを追加し、Stepsに複数処理を上から順に登録します。
4. 詳細画面でテスト実行し、内容を確認してから手動実行します。
5. 無人実行する場合は利用者のCloudflare Workerを接続します。worker/center-wrangler.example.jsoncが1分間隔のResoArc Clock設定例です。
6. 外部には管理アプリID、kintoneドメイン、APIトークンを設定します。バッチ定義の個別コピーは不要です。

## 重要事項

- 管理アプリだけでは無人の時間起動はできません。外部側で定期的な時刻チェックが必要です。
- Workerは期日を迎えた管理レコードを探し、リビジョンを照合して実行中に変更します。
- 一連の更新は自動ロールバックされず、失敗後は要確認にします。強制再実行は重複登録の危険があります。
- 最初はWorkerのRA_ALLOW_WRITES=falseで確認してください。真にすると対象データも更新されます。
- 対象レコードは最大100件、処理タスクは最大20件の開発版です。
- 本番kintone上での作成・結合試験とCloudflareへのデプロイはまだ行っていません。
