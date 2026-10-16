# ResoArc Clock：1分共通クロック導入（v0.3.4 検証版）

Cloudflare WorkersのCron Triggersを1つだけ使い、時刻を毎分チェックします。新しい適応型ポーリングではkintoneの照会は原則10分ごと＋実行予定時に絞り、管理アプリに記録された20ステップ以内の処理を実行します。

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

- 適応型では予定がない日のkintone検索は約144回/日、従来の毎分モードでは1,440回/日です。実際の処理APIは別途加算されます。
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

## v0.3.2 起動時の安全条件

Clockは `RA_CLOCK_ENABLED` が文字列の `true` と完全一致する場合にのみ起動します。設定が欠けていたり `yes` や `1` となっていたりする場合は、kintoneへ通信しません。旧JSON直接実行モードでも同様です。
## v0.3.3 適応型ポーリング（推奨）

Cloudflare Cronは毎分起動しますが、KVに記録した最短の次回バッチ実行時刻と10分の再同期期限を確認し、不要なkintone REST APIを呼び出しません。

- 新規セットアップの初期値は `RA_POLL_MODE=adaptive` です。適応型にはCloudflare Workers KVの `RA_CLOCK_STATE` バインディングが必須です。
- 仕事がない日のシミュレーション: **kintone 144回、KV読み取り1,440回、KV書き込み144回/日**。毎分1,440回の直接ポーリング比で、kintone照会は90%減ります。
- 最短実行時刻の到来をキャッシュで検知した場合は、kintoneの管理アプリから次回予定と実行待ちを取得して実行します。既存のリビジョン照合を維持します。
- バッチ設定の作成・変更・停止をCloudflareに即時通知する仕組みはまだないため、再同期間隔の最大約10分にKVの伝播遅延が加わり得ます。Cloudflare KVは結果整合性であり、リージョン間で約60秒程度の反映遅延があり得ます。
- 毎分の実行待ちが存在する場合はkintone側の照会も毎分必要になります。
- KV書き込みは最短2分間隔。毎分バッチがある場合も概ね720回/日に抑えます。ただし他のツールと同一CloudflareアカウントのKV無料枠を共有する場合は全体の利用量を確認してください。
- KVが利用できない場合は**毎分kintone照会へ自動フォールバックしません**。エラーで停止し、復旧後に再同期します。
- 旧環境との互換性のため `RA_POLL_MODE=minute` を明示した場合は従来方式を利用できます。設定を省略した既存Workerも従来方式を維持します。

### KVを自分のCloudflareアカウントに作成

既存のClockをすでに持っている場合は、CloudflareのKV領域を用意し、**公開しないローカル設定ファイル**にIDを追加してデプロイします。

```powershell
Set-Location .\worker
npx wrangler kv namespace create RA_CLOCK_STATE
```

出力されたNamespace IDを、Gitに含めない `wrangler.clock.local.jsonc` に記載します。

```json
{
  "kv_namespaces": [
    {"binding": "RA_CLOCK_STATE", "id": "発行されたNamespaceID"}
  ]
}
```

これはローカル設定ファイルへの**追加部分**です。元のCron/vars/name/entry pointを置き換えないでください。

```powershell
npx wrangler deploy --config wrangler.clock.local.jsonc
```

設定は `RA_CLOCK_ENABLED=false` のまま実デプロイして構いません。Clockが停止している間はkintoneへアクセスしません。kintoneのテスト管理アプリ・専用のSecret設定が整ってから、読み取り専用の `RA_ALLOW_WRITES=false` で開始してください。

公式資料:
- https://developers.cloudflare.com/kv/platform/limits/
- https://developers.cloudflare.com/kv/concepts/kv-bindings/
- https://developers.cloudflare.com/kv/concepts/how-kv-works/
