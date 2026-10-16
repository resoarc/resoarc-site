# ResoArc Batch Flow: 自分で時間実行するためのガイド

**毎分共通クロック型の新しい設定は [CLOCK.md](CLOCK.md) を参照してください。** このページは従来の1フロー単位Cron設定の説明です。

外部連携は任意です。手動実行だけなら、この設定は不要です。APIトークンをResoArcへ送る必要はありません。

## A. kintone側の準備
1. プラグイン設定画面でタスクを上から順に作り、保存する。
2. アプリの設定を更新し、レコード一覧に戻る。
3. 「実行内容を確認（テスト）」で対象件数と順序を確認する。
4. プラグイン設定画面の「外部スケジュール連携」でJSONを生成する。
5. 対象アプリごとに必要最小限の権限でkintone APIトークンを発行する。

## B. Cloudflare Workers側の準備
Node.jsを導入し、本リポジトリの `worker` ディレクトリに移動する。

```sh
cd worker
npx wrangler login
npx wrangler deploy
```

Cloudflareのアカウント上で料金プランと利用制限を確認してから進める。

## C. CloudflareのSecret設定

```sh
npx wrangler secret put KINTONE_DOMAIN
npx wrangler secret put KINTONE_API_TOKENS
npx wrangler secret put WORKFLOWS_JSON
```

それぞれに、kintoneのドメイン名（例: `example.cybozu.com`、`https://` は付けない）、APIトークン（複数ある場合はカンマで連結）、プラグインで生成したJSON全体を登録する。

* APIトークンはリポジトリ、プラグイン設定、サイト公開ページなどに記載しない。
* 複数アプリにアクセスする場合は、対象アプリそれぞれでトークンを発行する。
* アプリの閲覧・編集・追加など、処理内容に応じたAPI権限が必要。

## D. 実行時刻の設定

`worker/wrangler.jsonc` の `triggers.crons` を編集し、プラグインが出力したJSONの `cron` と同じ時刻を設定する。

| 日本時間 | Cron（UTC） |
| --- | --- |
| 毎日 03:00 | `0 18 * * *` |
| 毎日 09:00 | `0 0 * * *` |
| 毎日 18:30 | `30 9 * * *` |

複数の時刻が必要な場合、配列に値を追加する。Cron設定を変更したら `npx wrangler deploy` を再実行する。Cloudflareの無料プランにはトリガー数や実行時間などの制限がある。

## E. 安全な試運転と有効化

1. 初期設定 `RA_ALLOW_WRITES=false` のまま実行し、Worker Logsに表示されるタスク順・件数を確認する。
2. テスト用アプリなどを使ってデータ変更が意図どおりか確かめる。
3. 本番データをバックアップする。
4. 自動書き込みする場合のみ `RA_ALLOW_WRITES=true` に変更し、再デプロイする。
5. スケジュールを停止するときはCron Triggerを無効化し、Worker Logsを確認する。

## 重要な制限

- 1回の取得は最大100件、1フローは最大20タスク。
- 失敗したタスクより前のデータ変更は自動的には戻らない。
- 登録と転記は再実行で重複する場合がある。初期版は重複防止や実行ロックが未実装。
- 手動ボタンは現在ログイン中の権限、自動実行はAPIトークンの権限で動く。
- プラグイン側のフローを変更したら、JSONを再生成してWorker Secretに設定し直す。
- Workerは公開URLからの実行には対応しない。Cronのみで実行する。
- CronはUTCで指定する。表示時刻と実行時刻の取り違えに注意。

## 参考公式ドキュメント

- kintone REST API: https://cybozu.dev/ja/kintone/docs/rest-api/overview/kintone-rest-api-overview/
- Cloudflare Cron: https://developers.cloudflare.com/workers/configuration/cron-triggers/
- Cloudflare Secrets: https://developers.cloudflare.com/workers/configuration/secrets/
