# ResoArc Clock v0.3.5: Live Read-Only E2E

Date: 2026-10-17
Status: DEVELOPMENT PREVIEW. Writing-business-record E2E is not completed.

## Completed in the dedicated test tenant

1. Verified a dedicated Batch Center test management app exists with the expected fields, Steps subtable, and enabled plugin.
2. Issued a new **view-record-only** kintone API token. Confirmed add, edit, delete, and app management permissions were all disabled.
3. Saved and applied the token configuration. Confirmed a real authenticated REST GET for the test management app returned HTTP success.
4. Sent tenant hostname and token **directly from an on-device process into Cloudflare Worker Secrets**. Neither appears in public source, console output, nor release archives.
5. Enabled Cloudflare Cron-only Worker in adaptive mode, manager app set to the test app, and **RA_ALLOW_WRITES=false**.
6. Verified Worker wrote sync state to Workers KV following a scheduled kintone read.
7. Created one disposable test-management record containing a read-only step pointing to the same test app.
8. Invalidated only the test app's KV schedule cache for prompt reconciliation.
9. Observed a real Cloudflare scheduled run: one manager-app poll, one DRY RUN evaluation, no unexpected API errors.
10. Stopped the test-management record; confirmed no currently enabled scheduled records remain.
11. Observed KV cache returned to **nextDueAt=null**, with a ten-minute resync interval.

## Source changes

- Corrected preview app-deploy API method to **POST**, the documented method for /k/v1/preview/app/deploy.json. Bootstrap generator and tests now agree.
- Retained the NextRunAt != "" filters, preventing unscheduled draft records from starving scheduled tasks.
- Local-only credential-handling and browser-test scripts remain ignored by Git, excluded from source ZIP.
- Added safe remote-tail verifier that outputs aggregate counts instead of raw provider logs.

## Current cloud state

- RA_CONTROL_APP_ID: dedicated test management app
- RA_CLOCK_ENABLED: true
- RA_POLL_MODE: adaptive
- RA_ALLOW_WRITES: false
- Workers KV: bound and verified
- workers_dev / preview_urls: disabled
- Actual business records modified by Worker: none
- kintone business writes: not attempted

## Before v1.0

1. Create a separate disposable target test app and least-privileged write token.
2. Verify claim/finalize state transitions, one-time disable, multi-step updates, revision conflicts, and recovery with reversible test data.
3. Confirm live Cloudflare quota usage across other Workers.
4. Perform source code and identity/privacy checks before publication.

Official API documentation: https://kintone.dev/en/docs/kintone/rest-api/apps/settings/deploy-app-settings/

## 追補：Cron書込みE2Eの安全上の保留（2026-10-17）

Cron→KV→kintoneのDRY RUNは確認済み。次段階の管理レコードに対する自動書き込み試験は、Cloudflare CLIの非対話認証要件でデプロイ前に中断したため、**PASS扱いしません**。

一時的に用意したテスト管理レコードは停止・削除済みです。管理アプリの自動実行有効レコードは0件、業務QAデータは残件0件です。最後に読取検証できたCloudflare配備バージョンは `RA_ALLOW_WRITES=false`。認証エラーが解消するまで遠隔状態の再照合は保留とします。

`npm run cloud:preflight` を追加し、書込み禁止の安全な設定に加えて対象Workerの配備一覧取得権限を確認します。`wrangler whoami`が成功しても対象WorkerのCLI APIにアクセスできない場合は`ready=false`で停止します。Cloudflareログインは所有者が専用ブラウザーで再認証し、秘密値をソースに含めない運用とします。

詳細: `docs/CLOUDFLARE-KINTONE-STAGING-20261017.md`。
