# ResoArc Clock v0.3.4: 安全性・kintone実環境照合

更新: 2026-10-17
判定: **検証版**。管理アプリ・手動バッチのkintone実環境書込みE2Eは合格。Cloudflare Cronからの無人実行E2Eは未実施。

## 今回の修正

- kintoneの日時フィールドが空欄のレコードを、管理アプリ検索条件 NextRunAt != "" で除外。毎分モードとKV適応型の双方に適用。空欄レコードが多数あっても期限到来バッチが検索から押し出されないテストを追加。
- kintone公式仕様と実テナントでの成功結果を照合し、アプリ設定反映のHTTPメソッドにはPOSTを使用。生成スクリプトにも反映。
- Mole Remoteのkintone高速テストから認証・API読取・専用ブラウザーの疎通を確認。
- 専用のResoArc Clock検証用管理アプリ（ID 50）が既に作られていたため、重複作成を中止。フィールド構造・テーブル列・プラグインの有効状態を読み取り検査した。
- 実テストテナントで、空欄日時除外を含む管理アプリ検索クエリをREST GETで実行し、正常に受け付けられることを確認（返却0件）。業務レコードの追加・更新・削除は行っていない。

## 検証ステータス

- npm test：追加テストを含む全件合格。
- npm run test:mr-readiness：staging_ready_for_control_app_e2e / appId 50 / pluginEnabled true / missingFields []。
- node scripts/mr-clock-query-preflight.mjs：queryAccepted true / returnedRecords 0。
- Cloudflare Worker：既存の RA_CLOCK_ENABLED=false / RA_ALLOW_WRITES=false / RA_CONTROL_APP_ID=0 を維持。
- 署名済みCenterプラグインはv0.2.1。新たな署名鍵を生成・公開しない。
- 新しいAPIトークン、秘密鍵、クッキーをソース・配布ZIPに埋め込まない。

## 次の検証

1. 検証用管理アプリID 50向けに最小権限APIトークンを安全にCloudflare Secretsへ保存（権限確認後）。
2. Clockを RA_ALLOW_WRITES=false で有効化し、Cloudflare Cron→KV→kintoneの読取E2E、通信件数を監査。
3. 新しいテスト用の無害なレコードだけを対象とし、明示した試験手順と復旧手順に従い書込みE2E。
4. 同時刻2件超、KVの一時障害、時刻変更、revision競合、実行途中障害を実環境で検証。
5. kintone本番運用、GitHub正式公開、ResoArcサイト掲載は実機検証後とする。

## 参考

- https://jp.kintone.help/k/ja/trouble_shooting/app_qa/filter_empty
- https://cybozu.dev/ja/kintone/docs/overview/query/
- https://cybozu.dev/ja/kintone/docs/rest-api/apps/form/add-form-fields/
- https://developers.cloudflare.com/kv/concepts/how-kv-works/

## Cloudflare反映結果

v0.3.4の適応型Workerを、停止設定のまま既存のCloudflare Cron-only Workerへ再デプロイ済み。毎分CronとKVバインディングは維持し、公開URL・プレビューURLは無効化。RA_CLOCK_ENABLED=false / RA_ALLOW_WRITES=false / RA_CONTROL_APP_ID=0 を再確認したうえでデプロイした。実kintoneへの通信は開始していない。

## 追補：Batch Center手動実行の実テナントE2E（2026-10-17）

MRの専用Edgeを使い、新規に用意した管理アプリ・QAデータアプリだけを操作して以下を検証しました。

- Batch Centerプラグインv0.2.1をシステムに導入し、管理アプリへ追加。フォーム・テーブル・詳細画面上のボタンを確認。
- 読取専用フローのテスト実行（revision・状態・履歴不変）、手動実行（正常終了・履歴保存）。
- **取得→更新→転記→登録**の4タスクを、まずドライランで確認し、次にkintoneへ実書込み。転記後のフィールド値を含め、想定どおり3件となることを確認。
- 無害な検証用レコード3件だけをID・検証キー照合後に削除。**QAデータアプリの残件0**を確認。
- 不正なフィールドを指定した失敗フローで「要確認」に遷移し、再実行が拒否されること、revisionと履歴が増えないことを実画面で確認。
- 管理アプリのバッチは全件「自動実行＝停止」を確認。既存の業務アプリおよび自動採番検証アプリに対する書込みは行っていません。
- `npm test` は **73件中73件成功**。

詳細は `docs/REAL-KINTONE-STAGING-E2E-20261017.md` を参照してください。**Cloudflare Cron → KV → kintone** の無人実行E2E、および実ネットワーク切断やKV障害からの復旧試験はまだ行っていません。実Cloudflare Workerは引き続き停止状態のままです。

## 追補：Batch Center手動実行の実テナントE2E（2026-10-17）

MRの専用Edgeを使い、新規に用意した管理アプリ・QAデータアプリだけを操作して以下を検証しました。

- Batch Centerプラグインv0.2.1をシステムに導入し、管理アプリへ追加。フォーム・テーブル・詳細画面上のボタンを確認。
- 読取専用フローのテスト実行（revision・状態・履歴不変）、手動実行（正常終了・履歴保存）。
- **取得→更新→転記→登録**の4タスクを、まずドライランで確認し、次にkintoneへ実書込み。転記後のフィールド値を含め、想定どおり3件となることを確認。
- 無害な検証用レコード3件だけをID・検証キー照合後に削除。**QAデータアプリの残件0**を確認。
- 不正なフィールドを指定した失敗フローで「要確認」に遷移し、再実行が拒否されること、revisionと履歴が増えないことを実画面で確認。
- 管理アプリのバッチは全件「自動実行＝停止」を確認。既存の業務アプリおよび自動採番検証アプリに対する書込みは行っていません。
- `npm test` は **73件中73件成功**。

詳細は `docs/REAL-KINTONE-STAGING-E2E-20261017.md` を参照してください。**Cloudflare Cron → KV → kintone** の無人実行E2E、および実ネットワーク切断やKV障害からの復旧試験はまだ行っていません。実Cloudflare Workerは引き続き停止状態のままです。
