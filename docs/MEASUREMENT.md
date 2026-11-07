# ResoArc privacy-first activity measurement

Status: **code prepared, not live until Cloudflare binding and deployment are verified** (2026-11-08).

## Purpose and boundaries

The Pages advanced-mode Worker (site/_worker.js) records aggregate-only events:

- page_request: successful GET of an HTML page.
- download_request: successful GET (or redirect under HTTP 400) of /downloads/*.zip. A download request is not proof that the ZIP completed, was installed, or was used.
- Each record has UTC day, event type, canonical pathname and a **coarse source category**: internal, note.com, github.com, Google, Bing, Yahoo, DuckDuckGo, direct, other or unknown.
- No IP address, cookies, tracking ID, user agent, query string, raw referrer, or user-specific identifier is written by this application.
- This does **not** measure unique visitors or detect blocked clients. Bots, caching, redirects, offline usage and repeat requests can skew counts. It must not be represented as installation counts.
- Analytics never blocks delivery of a file/page: write failures are ignored after request handling.

## Activation (operator only)

1. Review Cloudflare Analytics Engine pricing, account retention, dataset permissions and privacy notice.
2. Create a Cloudflare Analytics Engine dataset and bind RESOARC_ACTIVITY to the existing Pages Worker in production. Do not create a client-tracking token or expose Cloudflare credentials.
3. Verify Workers runtime supports writeDataPoint and ctx.waitUntil, and that production deploy preserves the binding. Deploy only with scripts/deploy_canonical.ps1 after complete verification.
4. Fetch a test HTML page and an actual ZIP request with a known Referer; inspect the private dataset (not public website) for two rows with day, kind, path, source.
5. Compare daily trends before/after coverage by note.com, detect possible bot traffic, and mark incomplete periods explicitly. Do not publicly release raw per-request data.

The binding is **optional**: without it, all pages and downloads work as before but zero activity rows are written. No claim of active measurement is valid until the operator has confirmed a dataset exists and actual events are arriving.

## Suggested dashboard

Daily page requests; daily ZIP requests by product basename; daily source group; note.com -> product interest before/after media coverage; 7-/30-day moving trends. Display event counts and coverage status. Do not infer unique people, downloads completed, review sentiment, or conversions without corroborating evidence.

## Validation

Run node --check site/_worker.js and node tests/worker_activity.test.mjs.

See site/privacy/ for the public data-handling notice.

## Querying aggregate events (private)

Cloudflare Analytics Engine SQL API returns sampled aggregates; account for the sampling interval rather than treating raw row count as complete traffic. Example query (replace dataset after setting up the binding):

    SELECT blob1 AS utc_day, blob2 AS event_type, blob3 AS path, blob4 AS source,
           SUM(_sample_interval) AS estimated_requests
    FROM resoarc_activity
    WHERE timestamp > NOW() - INTERVAL '30' DAY
    GROUP BY utc_day, event_type, path, source
    ORDER BY utc_day DESC LIMIT 1000

The dataset is created on first write after binding. The provider documents approximately three months of analytics retention; longer monthly history must be exported through an authorized, access-controlled channel with no user-level identifiers. Do not publish raw rows. Reference: https://developers.cloudflare.com/analytics/analytics-engine/get-started/ .
