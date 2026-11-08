# ResoArc production / GitHub reconciliation, 2026-11-08

## Cause

The Cloudflare Pages project `resoarc` uses **Direct Upload**, not
GitHub-linked automatic deployment. Isolated site-building worktrees had been
uploaded independently, while the official GitHub `main` stayed behind.

## Evidence and source selection

- Public production sitemap: **54** routes.
- Official GitHub `main` prior to this merge: **37** routes.
- Production-only routes: **27**. Main-only routes: **10**.
- Verified local release source: `integration/kintone-three-release-prep-20261107/site`
  (54 routes, 331 files). This is a separate, preserved operator worktree.
- **145 of 145** linked public static and data files matched that source by
  downloaded bytes and SHA-256.
- Of the 53 HTML pages fetched initially, **48** had matching parser-extracted
  text; the remaining pages may be affected by Cloudflare's HTML processing
  and should not be treated as byte-identical.
- All three previously unlocated product pages were found in that release
  worktree: `input-template`, `mail-compose`, `reuse-reset`.
- Initial transient failure loading `/tools/kintone-auto-number/` was retried,
  and a later HTTPS request returned HTTP 200.
- Reconciliation preserves the union of both site maps: **64 routes**,
  with a source tree of **339 files**.

## Merge and safeguards

1. Restored the verified public source as the baseline without erasing the
   eight previous-main-only files.
2. Merged the release Worker's SWWW read-only API and Outage Radar handlers
   with official main's optional privacy-minimized Analytics Engine tracking
   and live OpenSSF Scorecard handler. Keep explicit historical fallback.
3. Set `_routes.json` to invoke the Worker for pages, downloads and APIs
   (excluding normal `/assets/*` static files), rather than routing only
   `/api/scorecard`.
4. Merged production HSTS, CORS and Content Security Policy with narrowly
   scoped official badge image origins.
5. Updated the privacy notice to disclose potential optional aggregate
   telemetry and made new community pages discoverable.
6. Updated the ISO verification rule: a public ISO link, if advertised,
   must include a matching digest; the site currently states that the
   experimental ISO is not available for general distribution.
7. Added a **fail-closed** live-data guard checking three independently
   published SWWW files for exact byte matching. Deploys must also retain
   every live sitemap route.
8. Two synthetic credential URLs in the published ZIP's security test fixtures
   are narrowly exempted from the secret scanner using exact SHA-256 hashes
   of their original lines. All other secrets remain blocked.

## Acceptance evidence

- `python scripts/verify_site.py`: PASS.
- `python -m unittest discover -s tests -p test_*.py`: 20/20 passed.
- `node --check site/_worker.js`: PASS.
- `node --test tests/test_site_worker_reconciled.mjs`: 7/7 passed.
- `python scripts/check_repository_secrets.py`: 0 findings.
- `python scripts/verify_live_route_preservation.py`: 54 live
  routes retained by 64-route candidate.
- `python scripts/verify_live_data_preservation.py`: 3/3 live SWWW
  files equal.

A merged PR alone does **not** synchronize production. Full completion
requires merging to official GitHub `main`, Direct Upload of that exact
commit with the guarded deploy script, and live HTTP/API smoke tests.
