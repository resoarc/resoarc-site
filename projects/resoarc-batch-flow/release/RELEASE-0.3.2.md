# ResoArc Batch Flow / Clock v0.3.2 | Development Preview

Date: 2026-10-17
Status: **Preview only. Not approved for a production tenant.**

## Safety changes
- All scheduled modes now require the explicit setting `RA_CLOCK_ENABLED=true`; absent, false, or mistyped values remain disabled.
- A manually executed batch in `要確認` state is blocked until an administrator inspects affected records and changes the status to `待機`.
- Successful one-time jobs cannot be rerun manually without a deliberate operator reset to waiting.
- The Cloudflare adapter now passes the `id` parameter correctly on single-record GET and limits allowed REST operations by endpoint.
- Kintone HTTP 409 errors continue to preserve their status so competing claims are not retried as business writes.
- Added browser simulation tests for manual run and API adapter safety.

## Verification checklist
- `npm test`: must pass all cases, including disabled scheduling, duplicate prevention, and manual preview.
- `npm run build:installer`: generate one-time test-tenant app bootstrap.
- Build signed center plugin v0.2.1 locally. The private signing key must **never** be committed or included in a public source archive.
- `npx wrangler deploy --dry-run --config center-wrangler.example.jsonc`: verify bundle compilation without publishing.

## Not verified
- Live kintone tenant app provisioning / E2E writes.
- Production Cloudflare credentials and HTTP permissions.
- Recovery from a crash between a business write and the final log write.
- Guaranteed idempotent record creation when an operator deliberately resets a failed job.
- Actual kintone per-app quotas and field-level permission behavior.

## Deployment policy
Keep the existing draft PR and preview branch. No merge to `main`, production site release, or auto-enabling of Cloudflare Clock until live staging checks and independent review are completed.
