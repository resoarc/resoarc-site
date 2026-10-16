# ResoArc Clock: Cloudflare Cron × kintone実環境検証

検証日: 2026-10-17（日本時間）  
対象: ResoArc所有者の検証用kintone管理アプリ（アプリID 50）  
構成: Cloudflare Cron Triggers → Worker → KV（RA_CLOCK_STATE） → kintone REST API  
公開可否: **開発プレビュー。正式リリース判定ではない。**

## Cloudflare配備確認

- 診断時の稼働Workerは旧バージョンで、`RA_CLOCK_STATE` バインディングと`RA_POLL_MODE`が未設定だった。
- Git管理対象外の安全設定を確認して再デプロイ。`RA_CONTROL_APP_ID=50`、`RA_CLOCK_ENABLED=true`、`RA_POLL_MODE=adaptive`、**`RA_ALLOW_WRITES=false`** を稼働バージョンのバインディングから再確認。
- Workerの`workers_dev=false`、`preview_urls=false`を維持し、パブリック実行URLを有効化していない。
- `KINTONE_DOMAIN` と `KINTONE_API_TOKENS` はCloudflare Secret名の登録だけを確認。**値は読み出さず、ログ・GitHubに記録しない**。

## 実Cron・KV・kintone接続

- 再デプロイ後、KVに管理アプリ50の状態キーが生成された。
- KV状態のJSONは`v=1`で、`syncAt`が記録され、次の実行予定がない状態では`nextDueAt=null`。
- この状態はWorkerがKVを読み込み、kintone管理アプリの予定検索を実行してから状態をKVへ書き込むことで生成される。Cronの実稼働とkintone照会成功の根拠となる。

## 読取専用の期日到来バッチ検証

安全性のため、**Workerの業務・管理レコード更新許可はfalseのまま**にする。検証用の取得1ステップだけを持つ管理レコードを一時的に`有効`・期日到来へ変更し、予定検知とドライラン、データ不変を確認する。終了後は管理レコードを元の`停止`へ戻し、試験用KVキャッシュを再同期させる。

**実測結果: PASS。** アプリ50の読取のみの検証バッチ1件を予定到来にし、CronによるKV状態（nextDueAt）の生成・予定検知を確認。Workerの書き込みは禁止したまま、QA業務データと実行履歴は変化しなかった。試験後は管理レコードを「停止」「正常終了」などの元状態に復元し、KV状態キーをクリアした。記録はMR専用レポート配下へ保存した。

この段階の検証は、管理アプリのテスト用レコード編集以外に、業務データの更新・転記・登録を行っていない。

## 残る課題

- `RA_ALLOW_WRITES=true`で実行される**Cron起動の書き込みE2E** は未検証。独立したテストデータ、最小権限、復旧を整備した上で実施する。
- 通信障害・KV障害、Worker強制終了、複数Cron競合、結果不明時の冪等性、モバイルの検証が必要。
- 現時点のテストに成功しても、無条件の自動再実行やバッチ全体のトランザクションロールバックを保証しない。

## 無人書き込み試験の試行と復旧

- kintone管理アプリのみを更新する「取得1ステップ」の一回実行テストを別途準備し、Cronの状態遷移・履歴記録の検証を試みた。
- **Cloudflare CLIの非対話認証条件で失敗し、書き込みを許可するWorkerのデプロイは成功していない。** よって無人書き込みE2Eの結果は **未検証** と判定する。
- 検証レコードは「自動実行＝停止」へ戻した後、IDと名称を照合して削除。管理アプリ側の有効なバッチは0件、QAデータアプリの残件は0件。
- 最後に実際のデプロイ内容を読取確認できた時点では、`RA_ALLOW_WRITES=false` の適応型Workerだった。その後の書き込み許可への変更はCLI認証エラーで失敗したが、現行デプロイを再確認するにはCloudflare再認証が必要。
- ローカルの`wrangler.clock.local.jsonc`は`RA_ALLOW_WRITES=false`へ復元済み。**公開用のソースにCloudflare・kintoneのトークンを格納していない。**

### Cloudflare再認証とアクセス確認

```powershell
cd worker
npx wrangler login
cd ..
npm run cloud:preflight
```

`cloud:preflight`はローカル設定が「管理アプリ有効・書込禁止・非公開Cron・KVあり」であることに加えて、**対象Workerのdeploymentを実際に一覧取得できること**まで確認する。単なる`wrangler whoami`成功では通過させない。CLIで再認証が必要な場合は、所有者自身のブラウザーでCloudflareのログイン・同意を完了する。アカウント情報やトークンをチャットに貼り付けない。

## 現時点の最終ステータス

| 検証 | 判定 |
| --- | --- |
| 実Cron発火 / KV更新 / 管理アプリGET | **PASS** |
| 期日到来バッチのDRY RUN / データ不変 | **PASS** |
| kintone内の4タスク手動E2E | **PASS** |
| Cloudflareからの自動書込み | **未検証（CLI認証で中断）** |
| QAデータの後片付けと全バッチ停止 | **PASS** |
| Cloudflareの最新稼働バージョン再照合 | **再認証後に実施** |
