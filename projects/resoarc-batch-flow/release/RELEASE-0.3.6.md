# ResoArc Clock v0.3.6: Safe Write E2E Preview

Date: 2026-10-17 (JST)
Status: **Development preview**. Do not claim Cloudflare write-mode acceptance or a v1.0 release.

## Completed this iteration

- Created and verified an isolated kintone sandbox App 52, with fields TestKey, Stage, Payload; no existing business apps were used.
- Implemented a temporary **E2E-only guard**. If RA_E2E_ONLY_BATCH_ID and RA_E2E_ALLOWED_APP_ID are set, both IDs must be valid, the due-query is restricted to the exact test batch, and read/create/copy/update steps are rejected unless their target/source is the configured sandbox App.
- Executed shared ResoArc engine with a real kintone session: create, read, update, copy; verified results and deleted both test records.
- Executed the real Batch Center dispatcher against kintone Apps 50 and 52 directly (not through Cloudflare):
  - Revision-based claim succeeded.
  - Read, update, copy and create steps succeeded.
  - Result finalized as 正常終了; one-time job auto-disabled.
  - Second invocation did not run again.
  - 3 target records and 1 manager record were removed after success.
- Tested true revision-race handling: forced a manager-record update between query and claim; kintone returned GAIA_CO02. After mapping that documented revision-conflict code, the second claim was correctly skipped. No target record created; manager test record removed.
- Tested real partial-failure protection: first step created a sandbox record, second step requested an intentionally invalid field and failed (GAIA_IQ11). Manager state became 要確認 and the next invocation did not repeat the create. The target record and manager record were removed.
- Worker REST adapter now preserves a bounded kintone error code without revealing response details. GAIA_CO02 can be recognized as a stale revision in addition to HTTP 409.

## Test result

- npm test: use the final invocation's passing result. Tests include safe E2E allowlist and GAIA_CO02 regression coverage.
- MR scripts for privileged test interactions remain local, ignored by Git and intentionally excluded from the public ZIP.
- No secrets, API tokens, or personal profile information are included in source/release packaging.

## Live Cloudflare limitation

Wrangler OAuth login expired/disconnected during this iteration. Attempts to deploy the new scoped Worker were **not successful**. The deployed Worker still uses the previously verified v0.3.5 read-only configuration (RA_ALLOW_WRITES=false). The new E2E allowlist is **not yet deployed**.

Cloudflare Cron -> kintone read-only integration was confirmed in the previous iteration. This iteration verified direct kintone business writes, runner state transitions, conflict handling and partial failure using the same source engine, **not a Cloudflare scheduled write-mode run**.

When Cloudflare OAuth is restored:
1. Keep RA_ALLOW_WRITES=false while deploying the scoped new Worker.
2. Use a dedicated app 52 read/add/edit token and app 50 read/edit token. Do not reuse unrelated business app privileges.
3. Activate scoped batch test only with both allowed IDs configured, after verifying no unrelated active batches.
4. Run bounded write-mode Cron E2E, inspect logs, and restore RA_ALLOW_WRITES=false immediately.
5. Remove temporary write tokens and test records; verify live Worker configuration and KV cache.

## Release policy

No merge to main, no public site change, no v1.0 release until the real Cloudflare write-mode E2E, credential rotation, and independent review have passed.

References:
- https://kintone.dev/en/docs/kintone/rest-api/records/update-record/
- https://developers.cloudflare.com/workers/configuration/cron-triggers/

## Additional safety review (2026-10-17)

- Worker Cron entrypoint now rejects test-only scoping variables whenever no management-app binding is supplied, preventing the legacy `WORKFLOWS_JSON` route from bypassing the E2E app allowlist.
- Cloudflare preflight now checks **the latest deployed Worker version's actual bindings**, in addition to CLI authentication and read-only local configuration. A split rollout, absent deployments, invalid version metadata, unbound KV, missing required Secrets, unexpected management app, or `RA_ALLOW_WRITES=true` all produce a fail-closed result.
- Added regression tests for wrong target app, write-enabled remote version, missing KV, partial rollout and legacy-route bypass. Final local test suite: **89/89 PASS**.
- The target Cloudflare deployment is **not currently accessible from Wrangler without renewed interactive authorization**. `npm run cloud:preflight` therefore reports `ready=false`, correctly blocking unattended write E2E.
- Actual Cron write-mode execution remains **NOT VERIFIED**. Existing tests and docs must not be interpreted as permission to merge or claim production readiness.
- No tenant domain, tokens, user identity, private signing key, or local device paths are included in this public note.
