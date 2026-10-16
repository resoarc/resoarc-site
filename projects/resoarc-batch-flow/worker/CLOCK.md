# ResoArc Clock：1分共通クロック導入（v0.3.1 検証版）

Cloudflare WorkersのCron Triggersを1つだけ使い、kintoneのバッチ管理アプリのNextRunAtを毎分チェックします。予定に達したバッチだけ、管理アプリに記録された20ステップ以内の処理を実行します。

## 仕組みと実行モード

- 毎日 HH:mm（日本時間）、1～10080分間隔、指定日時の一回実行に対応。
- 一回実行は成功時に自動停止。処理失敗時は「要確認」として停止。
- 無料プランの50サブリクエスト/回という制約を守るため **1周期2バッチまで**。残りは次の周期で順次処理。
- 1周期の理論上限は管理アプリGET1回 + 2バッチ×（競合防止PUT1 + 最大20処理API + 結果PUT1）= 45リクエスト。
- 数分停止していた場合も、間隔スケジュールの未実行周期をまとめて再実行しません。次の予定時刻へ進めます。
- 複数人が同時に操作してもrevisionが一致した1件だけが実行権を取得します。
- 失敗・強制終了・ネットワーク応答不明時は安全優先。登録や転記を自動再試行しません。

## 初期導入

先に [control-app/SETUP.md](../control-app/SETUP.md) を参照し、kintone側の管理アプリを用意してください。Node.jsと、ご自身で管理するCloudflareアカウントが必要です。

PowerShell（リポジトリ直下から）:

    Copy-Item .\worker\center-wrangler.example.jsonc .\worker\wrangler.clock.local.jsonc

ローカル設定ファイルのRA_CONTROL_APP_IDを管理アプリIDへ変更します。初期値0は未設定です。
作成したwrangler.clock.local.jsoncは.gitignore対象なのでGitHubに含めないでください。

    Set-Location .\worker
    npx wrangler login
    npx wrangler deploy --config wrangler.clock.local.jsonc
    npx wrangler secret put KINTONE_DOMAIN --config wrangler.clock.local.jsonc
    npx wrangler secret put KINTONE_API_TOKENS --config wrangler.clock.local.jsonc

- KINTONE_DOMAIN: example.cybozu.com のようにホスト名だけ。https://は不要。
- KINTONE_API_TOKENS: 管理アプリおよび対象アプリのAPIトークン。複数のときはカンマ区切り。必要最小限の閲覧／登録／編集権限だけ付与。
- Cloudflare Secretsにトークンを保存し、ソースコードやResoArcの運営サーバーに登録しません。

## 3段階で有効化する

1. 初期状態はRA_CLOCK_ENABLED=false、RA_ALLOW_WRITES=falseです。Workerを配置してもkintone通信は発生しません。
2. Clockを読み取り専用で試すときは、RA_CLOCK_ENABLED=trueへ変更して再デプロイします。RA_ALLOW_WRITES=falseのままなので業務レコードは更新されません。Cloudflare Logsで対象バッチ・件数を確認します。
3. テスト用のkintoneアプリで書き込み確認し、バックアップを取得した後にRA_ALLOW_WRITES=trueへ変更して再デプロイします。最後に、kintone管理アプリ側で対象バッチを「自動実行＝有効」にします。

**即時停止** したい場合は、Cloudflare側でRA_CLOCK_ENABLED=falseに戻して再デプロイします。特定バッチだけ止めるならkintone側の「自動実行＝停止」を使います。

## 運用上の注意

- 1分チェックだけで1日1,440回のkintone検索APIを使用します（Clockが有効な場合）。実際の処理APIは別途加算されます。
- 既存の管理アプリでScheduleTypeやIntervalMinutesがない場合は毎日モードとして処理します。
- 動作検証中にCloudflare側のCronが毎分起動しますが、`RA_CLOCK_ENABLED=false` の間はkintoneへの通信を行いません。Cronそのものを止めるにはCloudflare側のトリガー設定を無効化してください。
- CloudflareのCron起動に遅延が生じる場合があります。秒単位の正確な実行は保証しません。
- Workerが強制停止した場合は「実行中」のまま残り、自動復旧しません。kintoneの業務データを確認してから手動で復旧してください。
- デフォルト設定で `workers_dev=false`、`preview_urls=false` を指定し、**公開URL自体を作りません**。Cron-only Workerとして匿名性を確保します。
- Cloudflare実アカウントへのCronデプロイは完了し、**Clock停止状態の実Cron発火ログを1件確認**しました（2026-10-16）。kintone接続と実テナントへの書き込み結合試験は未実施です。

公式ドキュメント:
- https://developers.cloudflare.com/workers/configuration/cron-triggers/
- https://developers.cloudflare.com/workers/platform/limits/
- https://kintone.dev/en/docs/kintone/rest-api/records/update-record/
