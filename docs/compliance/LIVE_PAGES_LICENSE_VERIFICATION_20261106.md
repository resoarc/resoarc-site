# ResoArc Cloudflare Pages licensing and live distribution verification

**Observed:** 2026-11-06 JST. **Official license criteria:** OpenSSF Baseline Level 1 OSPS-LE-02.02 and OSPS-LE-03.02.
**Decision:** Both still **Unmet**, pending full delivery and software-rights evidence. This document does not assert certification.

## Actual Cloudflare change

The authorized operator authenticated to the Cloudflare dashboard, account Pages project **resoarc**, with the following publicly visible hostnames:

- https://resoarc.com/
- https://www.resoarc.com/
- https://resoarc.pages.dev/

**Three enabled single-redirect rules**, each restricted to exact request paths and to the first two hostnames only, were deployed in the **resoarc.com** Cloudflare zone. They use HTTP **302** and target stable versioned GitHub Release URLs, not expiring GitHub CDN asset URLs:

| Exact path | Public result on both custom domains | Hash/byte verification |
| --- | --- | --- |
| `/downloads/LICENSE` | 200 after redirect to GitHub Release asset | 1,109 bytes, exact file content |
| `/downloads/NOTICE.md` | 200 after redirect to GitHub Release asset | 2,419 bytes, exact file content |
| `/downloads/resoarcos-pc-v0.1.1-dev-source.zip` | 200 after redirect, previously 404 | 101,001 bytes, SHA-256 matches historical audit |

Destination release: https://github.com/resoarc/resoarc-site/releases/tag/resoarc-osps-distribution-mirror-20261106 .

**No Cloudflare Pages full-site deployment or ZIP modification was performed.** Existing downloadable ZIP URLs were not globally rewritten. The Pages default hostname (`resoarc.pages.dev`) **still returns HTTP 404** for those three URLs.

## Live-source mismatch and why a full deploy was withheld

As checked on the same day, the production sitemap contains **51 public routes**, while current GitHub main source has only **36 HTML pages**. Production homepage/CSS differs significantly from the checked-out Git version. A direct upload of the GitHub `site/` directory could remove or revert current public pages, so full-site deployment remains **HOLD** until live content is reconciled and backed up.

The public `resoarc.com/downloads/` distribution was compared against the SHA-256 values in `docs/compliance/OSPS_RELEASE_LICENSE_AUDIT_20261106.json`:
- 10 of 20 ZIPs matched byte-for-byte.
- 9 of 20 were downloadable but their ZIP SHA-256 differed.
- 1 of 20, ResoArcOS PC v0.1.1 source, was 404 before the exact-path redirect and now matches the known release archive on both custom domains.

Seven differing **signed QA installers** have identical extracted inner source file content to the frozen archive, but differences in signed container bytes and signatures. This does **not** by itself establish cryptographic signature equivalence.

**Kanban** is different: the live signed QA ZIP has changed `js/core.js`, `js/desktop.js`, and `js/mobile.js` contents; the live Kanban alpha source ZIP also differs in six archive entries. Neither should be silently overwritten or described as the frozen historical version. A source/rights review and a new explicitly versioned release record are required.

## Acceptance gates

Before marking OSPS-LE-02.02 `Met`: identify actual public binary/source release components, map each to attributable source, verify license obligations and obtain accountable review of differing Kanban and legacy packages.

Before marking OSPS-LE-03.02 `Met`: prove that all official public release hosts provide each license alongside the corresponding assets. Verify live link discoverability, public Pages default hostname or explicitly document/remove it as a distribution channel, and repeat checksum checks after any deployment.

A future production update should import and reconcile the actual 51-route production snapshot into the authorized source of truth, pass staged content integrity tests, take a rollback point, and **only then** use the canonical Direct Upload process.

Follow-up issue: https://github.com/resoarc/resoarc-site/issues/74 . Official self-evaluation: https://www.bestpractices.dev/projects/15597/baseline-1 .

**No 100% or earned OpenSSF badge is claimed.**
