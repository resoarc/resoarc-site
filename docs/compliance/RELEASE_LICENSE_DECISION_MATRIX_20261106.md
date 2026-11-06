# ResoArc released-software license decision matrix

**Draft evidence for OSPS-LE-02.02 and OSPS-LE-03.02**  
**Created:** 2026-11-06. **Formal status:** NOT CLEARED, no final conformity claim.

## Observed evidence

The [immutable archive audit](OSPS_RELEASE_LICENSE_AUDIT_20261106.json) enumerates **20 historical downloadable ZIPs**, with independently checked sizes and SHA-256. All 20 byte-identical archives were published in the [GitHub historical mirror](https://github.com/resoarc/resoarc-site/releases/tag/resoarc-osps-distribution-mirror-20261106) with first-party LICENSE (MIT) and NOTICE as separate release assets; the owner-triggered archive job passed.

| Family | Quantity | ZIP licensing evidence | Outstanding obligations |
| --- | ---: | --- | --- |
| Signed kintone plugin installable packages | **11** | Outer archive includes signed `contents.zip`, public key and signature. No embedded LICENSE/NOTICE in the signed outer or inner archive. ResoArc source code uses MIT declarations via REUSE and the source repo. Eight QA versions are checked source-to-inner-archive by the suite16 release test. | Three older stable/beta packages need complete source correspondence verification; all copyright origins and third-party inclusions need a recorded approval. User-facing download flow must convey the matching LICENSE and NOTICE. Preserve signed inner bytes. |
| Source ZIPs for kintone alpha / Web8 / ResoArcOS PC/Pi | **9** | Archives contain LICENSE. Source-release CI compares immutable content and hashes for their documented scope. ResoArcOS source pyproject metadata declares MIT. | Verify full third-party dependency/license coverage and any source-offer obligations; snapshot release rights decisions must be signed off by a responsible maintainer. |

This is a file/rights *evidence inventory*, not legal advice and not an assertion that all packages have been cleared. The site also includes Noto Serif JP fonts (OFL-1.1) and an Unsplash-licensed photo. Those third-party works are not relicensed under MIT.

## To finish LE-02.02 (OSI / FSF-compliant released software license)

1. For **each of 20 assets**, map its exact SHA-256 to a source commit, authored files, authorship/permission evidence, third-party imports, and product-specific release notes.
2. Verify every actual bundled software component is distributed under an appropriate OSI/FSF-compliant software license. Record any separate font/photo material as such without presenting it as MIT software.
3. Verify whether any copied snippets, third-party libraries or build dependencies introduce special obligations. Keep unresolved cases **HOLD** instead of inventing a clean legal determination.
4. Obtain a real accountable maintainer's dated approval for each release family and preserve source-to-binary correspondence evidence. After that, update the official issuer answer with the audited component matrix.

## To finish LE-03.02 (license text delivered with release)

1. GitHub's historical mirror now has LICENSE and NOTICE adjacent to all 20 ZIPs; the source ZIPs also include LICENSE, but **signed plugins cannot be modified without re-signing**.
2. The Cloudflare production site's direct **/downloads/LICENSE** and **/downloads/NOTICE.md** previously returned HTTP 404. The remote Cloudflare dashboard requires a new authenticated session and no valid deployed change has been demonstrated. Do not claim these pages are fixed.
3. Restore ZIPs by executing `python scripts/verify_external_archive_mirror.py --hydrate` in the canonical deployment checkout and publish the hydrated site + LICENSE/NOTICE without changing the existing legacy download paths. Verify every page's adjacent license link, HTTP 200 and exact file checksum in production.
4. Record the deploying operator, timestamp, Cloudflare deployment ID, URL audit, response checks and test user receipt. Mark Met **only after real public distribution and third-party compliance requirements are proven**.

**Update 2026-11-06 JST:** The owner authenticated to Cloudflare and deployed three **exact-path 302** rules for the two official custom domains, serving LICENSE/NOTICE and restoring the missing ResoArcOS v0.1.1 source ZIP with byte-/SHA-verification. However the Pages default hostname still returns 404 for those files. A fresh 20-ZIP integrity check found 10 matching, 9 differing, and 1 originally 404 (now restored through a redirect). In particular, live Kanban JavaScript differs from the archived version. A full-site upload was intentionally withheld because the production sitemap has 51 routes versus 36 HTML pages in GitHub main. See [live distribution verification](LIVE_PAGES_LICENSE_VERIFICATION_20261106.md) and [issue #74](https://github.com/resoarc/resoarc-site/issues/74). Do not treat the two custom-domain fixes as universal delivery compliance.

**Status 2026-11-06:** both controls are still **Unmet** in the official OpenSSF self-assessment. This file must not be used as evidence of an earned badge.
