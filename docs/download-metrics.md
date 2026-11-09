<!-- SPDX-FileCopyrightText: 2026 ResoArc -->
<!-- SPDX-License-Identifier: MIT -->

# Download metrics (ResoArc public site)

## Coverage and definitions

- A Cloudflare Pages `_worker.js` counts **full successful HTTP 200 GET responses** through uncached `/api/v1/downloads/file?asset=resoarc*.zip` or `*.iso` delivery URLs, used by all direct ZIP/ISO links in the published catalog. It is not proof that the client received the whole file, nor a count of installations or unique humans.
- Legacy direct `/downloads/resoarc*.zip` paths are kept intact for backward compatibility and counted on an uncached Worker execution, but Cloudflare CDN cache hits can bypass the Worker. Those legacy routes cannot be guaranteed counted. The primary counted links route through an API path with an explicit `Cache-Control: no-store` response.
- Generated or new catalog pages must run `python -X utf8 scripts/route_public_download_links.py` before publishing; the script is idempotent.
- The response is served even if the counter database is unavailable. Only the non-blocking counter update fails.
- HEAD requests, partial Range requests, nonexistent paths, and non-200 responses do not increment. The delivery endpoint accepts only a strictly validated ResoArc ZIP/ISO filename; the file content remains identical and Content-Disposition retains the original filename.
- GitHub Releases file download totals are read independently from the public GitHub API and are not backfilled into D1. Automated requests and attachments such as LICENSE/NOTICE/SHA256SUMS may appear in GitHub totals.
- Do not sum both channels as distinct people. For identical asset names, downloads from separate channels are independent request counts.
- The database only stores UTC day, release filename, and cumulative daily request count. No IP, user agents, cookies, referrers, or per-person event logs.
- The dashboard lives at `/metrics/downloads/`. Public aggregate API: `/api/v1/downloads/summary`.
- Cloudflare Pages must be deployed with `wrangler.toml` from this release to bind D1 as `DOWNLOAD_DB`, preserving the existing `SWWW_LIVE` service binding.
- Site-direct statistics start on the production activation date. **No historical backfill** of site ZIP downloads is possible from this D1.

## Database

```powershell
wrangler d1 create resoarc-download-metrics
wrangler d1 execute resoarc-download-metrics --remote --file scripts/download_metrics_schema.sql
```

Database: `resoarc-download-metrics`. The database ID is a public, non-secret binding identifier in `wrangler.toml`.

## Verification

```powershell
node --check site/_worker.js
node --check site/assets/download-metrics.js
node --test tests/download_metrics.test.mjs
python -X utf8 scripts/update_manifest.py
python -X utf8 scripts/verify_site.py
```

Verify the preview API returns `site.available:true` and `github.available:true`, and verify a known ZIP GET increments exactly once while a HEAD does not. Restore the test baseline using a narrowly scoped D1 mutation after confirming no concurrent traffic.

## Safe deployment

1. Confirm the latest Cloudflare Production deployment's `Source` equals the checkout parent commit. Do not deploy a stale `site/`.
2. Ensure `wrangler.toml` still contains the production `SWWW_LIVE` binding and new D1 binding.
3. Deploy preview first, verify all existing routes (`/api/v1/swww/summary`, `/api/v1/outages`, `/os/`, kintone pages), and perform the counter test.
4. Deploy production via `wrangler pages deploy site --project-name resoarc --branch main --commit-hash <verified commit>`.
5. Confirm the production dashboard and its JSON API, and smoke-test existing endpoints. Capture a deployment URL.
6. If production regresses, rollback to the previously verified Cloudflare deployment `243887f5-8d6b-4a21-bb4d-1c43ee47ee93` from Cloudflare Deployments.

## Monitor and maintenance

Look for `site.available:false`, `github.available:false`, or an unexpected dip in daily counts. A site-direct count of zero is meaningful only when `site.available:true`. The GitHub API can be temporarily rate-limited; the dashboard must show unavailable, not zero. The public dashboard is for transparency, not telemetry of individual people.
