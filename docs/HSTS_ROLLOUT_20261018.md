# HTTPS/HSTS staged rollout

Start: 2026-10-17, `max-age=300` on `resoarc.com`, `www.resoarc.com` via Cloudflare Pages `site/_headers`.

2026-10-18: after confirming valid HTTPS, homepage, recognition, products, and www, prepared `max-age=604800` (7 days) for production. `includeSubDomains` and `preload` intentionally omitted.

## Operational rules
- After publishing, verify HTTP 200 and header `Strict-Transport-Security: max-age=604800` on apex and www and security.txt; monitor issues before further changes.
- Keep HTTPS enabled with valid managed certificates. Do not disable proxy, certificates, or change nameservers without considering HSTS clients.
- Wait at least the full 7-day stage before moving to one month (`2592000`) and at least that full month before one year (`31536000`). Do not accelerate to improve a badge.
- Rollback for future clients: publish `max-age=0` header. Existing visitors may still enforce the previous cached policy until they receive an HTTPS response carrying the new setting. If HTTPS itself breaks, HSTS can make recovery especially difficult.
- Internet.nl requires HSTS `max-age >=31536000` to count as sufficiently secure. Shorter staged headers do not satisfy that check.
- ResoArc DNSSEC remains disabled in registry RDAP as of review on 2026-10-18. Cloudflare account's available OAuth session did not authorize read access to zone DNSSEC. Do not claim DNSSEC is enabled.
- TLS cipher failures in Internet.nl may reflect Cloudflare edge cipher offering and require a plan-level setting or service-provider action. Avoid undocumented changes and do not conflate SSL Labs A+ with Internet.nl compliance.

References:
https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/
https://en.internet.nl/article/new-release-with-improved-tests-for-TLS-and-CSP/
https://internet.nl/site/resoarc.com/4355764/
