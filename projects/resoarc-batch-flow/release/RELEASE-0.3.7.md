# ResoArc Clock v0.3.7: safety-hardening preview

Release status: DEVELOPMENT PREVIEW, NOT a production release.
Date: 2026-10-17 (JST)

## Delivered

- Changed the worker's scheduled entrypoint so a single RA_ALLOW_WRITES=true flag never authorizes unrestricted production writes. A further RA_ALLOW_UNSCOPED_WRITES=true flag is required unless both test batch ID and sandbox app ID are present. This is a deliberate fail-closed change.
- Partitioned Cloudflare KV keys so isolated tests use separate cache entries per batch ID and dry-run / write phase. The original no-scope key is preserved to avoid disturbing existing read-only schedules.
- Kept the existing E2E-only allowlist for selecting one exact management job and restricting the business target app.
- Revalidated kintone integration behaviors from earlier test sessions: create/read/update/copy; claim/finalize and one-time disable; kintone GAIA_CO02 stale revision handling; non-retry after partial failure. Those tests involved dedicated disposable apps and were cleaned up.
- Added regression tests for default-deny unrestricted write mode and distinct KV schedule caches.
- Restored the local Wrangler configuration to read-only normal mode; removed temporary dummy batch allowlist settings. The configuration file is excluded from published sources.

## Validation

- Node.js test suite: 91 of 91 pass.
- Wrangler bundle dry-run: run separately to verify Cloudflare worker packaging.
- Release ZIP creator rejects text files containing local Windows usernames/paths or email-like strings and excludes private keys, local Cloudflare config, and session-authenticated scripts.
- Local source repository is staged for the anonymous ResoArc owner identity only. Public GitHub publishing and site listing remain out of scope for this preview.

## Blockers before public release

- The Cloudflare Wrangler OAuth session is not authenticated. As a result, the new worker cannot yet be deployed; the existing live worker was last verified in read-only mode.
- Perform Cloudflare scheduled write-mode E2E using a sandbox app, least-privilege token, one specific batch, and immediate restore of read-only mode.
- Verify deployed settings after authenticating and finish independent code review, account-limit check, and security disclosures.

## Intended deployment defaults

Keep RA_ALLOW_WRITES=false while upgrading. For production writes, do not enable RA_ALLOW_UNSCOPED_WRITES until the owner has reviewed intended job permissions and the write-mode runbook.

## 追補：Cloudflare無人書き込みの限定実環境試験（2026-10-17）

Cloudflare再認証後、検証ジョブID 10・書き込み対象アプリID 52に**限定して** `RA_ALLOW_WRITES=true` を一時的に適用し、Cronの実動作を確認しました。kintone管理アプリ50には正常終了・一回実行後の停止・履歴1件が記録され、データアプリ52に検証レコード1件が生成されました。検証後はWorkerを再び書き込み禁止に切り替え、さらに試験対象ID制限を除去した通常の読取専用構成へ戻しました。

Cloudflare配備履歴の書き込み許可版（2026-10-17 03:20:36 JST）と復帰版（03:21:19 JST）、kintone記録、削除後のQAデータ残件0件を照合しました。`npm run cloud:preflight`は最終確認時点で `ready=true`、`remoteReadOnlyVerified=true`。別途起動しかけたテストWorkerは事前条件不一致で**デプロイ前に中止**されました。

ただし、Cloudflare Secret `KINTONE_API_TOKENS` の閲覧専用への差し替えは**未実施**です。自動差し替えは秘密情報の安全制約で停止しており、秘密値は取得・記録していません。Cloudflare側で管理アプリ50の閲覧専用APIトークンに手動で戻してください。トークンをチャットには貼り付けないでください。

検証内容・残条件：`docs/CLOUDFLARE-WRITE-E2E-20261017.md`。本結果は限定スモークテスト合格であり、v1.0正式公開ではありません。
