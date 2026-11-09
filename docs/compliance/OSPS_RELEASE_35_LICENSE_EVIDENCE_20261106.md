# ResoArc OSPS Level 1: public release license evidence, 35 assets

**Audited:** 2026-11-06 JST. **Official controls:** [OSPS-LE-02.02 and OSPS-LE-03.02](https://baseline.openssf.org/versions/2026-08-28). **Status:** technical release distribution verified; independent legal ownership/rights approval **NOT YET RECORDED**.

## Reproducible observed evidence

- Exactly **35** public ZIP releases: **22 signed installers and 13 source/other ZIPs**. Hashes, lengths and origin repository/commit are pinned individually in [the machine-readable inventory](OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json).
- Official public download origins checked: `resoarc.com`, `www.resoarc.com`, `resoarc.pages.dev`. **105 of 105** download attempts returned HTTP 200 and matched expected file SHA-256/size. A product whose bytes differ on a future audit must not be silently substituted.
- A separate `/downloads/LICENSE` and `/downloads/NOTICE.md` returned HTTP 200 and matched exact expected bytes on **all 3 hosts (6/6)**.
- All **13 source archives** contain at least one LICENSE file. None of the **22 signed installers** has a standalone LICENSE inside the signed outer or `contents.zip`, so the companion LICENSE and NOTICE beside the download path is essential. Signed ZIP bytes must not be rewritten without a new authorized signing process.
- The public [license/sha catalog](/downloads/index.html) covers all 35 paths and shows companion license links per download. Its content and expected manifest are maintained in GitHub under `site/downloads/`; the mandatory CI check audits catalog coverage. Production availability of the newly added catalog must be **verified after deployment**, and is not asserted by writing this document.

## Third-party software/material distinguished from MIT

| Component | Distribution(s) | Evidence and license treatment |
| --- | --- | --- |
| ResoArc-authored software | All ResoArc releases | Project-author declaration: **MIT**; SPDX/REUSE and source repository license. Authorship/permission is an **owner's assertion**, not independently verified for every included line |
| QR Code Generator-related code | QR Code mobile signed plugin | `contents.zip/js/qr-lib.js` carries **MIT text, original Kazuhiko Arase copyright (2009), and Apache-2.0 text**. Both are OSI-recognized open-source software licenses; preserve both notices. [Upstream MIT](https://github.com/kazuhikoarase/qrcode-generator/blob/master/LICENSE) |
| `fflate 0.8.3` | Backup & Migration v1.0.0 distribution + source | **MIT**. Shipping ZIP contains `LICENSES/fflate-MIT.txt`, `NOTICE.md`, and license notice in generated JS. Copyright Arjun Barrett. [Upstream](https://github.com/101arrowz/fflate) |
| `esbuild 0.25.12` | Backup & Migration source build process | **MIT** build-only tool; not shipped as a runtime binary. [Upstream](https://github.com/evanw/esbuild) |
| Noto Serif JP font | Site recovered source archive | **SIL OFL 1.1**. Font/media-specific license; not incorrectly represented as ResoArc MIT |
| Unsplash architecture photograph | Site recovered source archive | **Unsplash License**, separate media rights, not OSI-software-licensed. Its inclusion in a source snapshot requires a precise release-scope/legal review |

The presence of an OSI-approved license does not, by itself, prove that a distributor was authorized to grant it, or that all upstream attribution terms have been fulfilled. The actual contents of the QR and Backup artifacts were examined, not merely their filenames.

## Source-to-signed-payload provenance: real remaining risk

[Source matching detail for each signed package](OSPS_SIGNED_22_SOURCE_CORRESPONDENCE_20261106.json) is based on SHA-256 file matches and exact Git blob identifiers against the public Codeberg tree at `8e279c5ec277032724dfe9a611ad148ee6fcf035`.

- **8/22** signed packages: all inner file bytes match tracked source.
- **4/22** older stable/beta packages: only some inner files match tracked source.
- **10/22** mobile signed packages: no byte-for-byte matches in the examined public Git tree/history. This is not evidence of copied or unlicensed software; it **means that exact original source/build provenance has not been proven** from the examined repository.
- The signed bytes themselves are securely preserved and live hashes matched an actual published archive. That establishes provenance of the *download*, not creation/ownership of the original code.

An authorized maintainer must either locate trustworthy original source/build records for the 14 partial/absent cases, or attest and version extracted payload source as an explicitly newly documented public snapshot, with the upstream license terms preserved. A generated extraction must never be described as an independently recovered authoring history.

## License delivery evidence and limitations

A companion LICENSE in the **same `/downloads/` directory namespace** as the exact release assets satisfies the publication *mechanism* described by OSPS-LE-03.02, provided it remains accessible and applicable to each release. On-chain ZIP signatures were not modified. A dedicated public catalog adds prominent links for user discoverability; see [catalog](../../site/downloads/index.html), [third-party notes](../../site/downloads/THIRD_PARTY_LICENSES.md), and [verification script](../../scripts/verify_osps_35_license_delivery.py).

If all live links pass after the catalog deployment, the **delivery** control can be truthfully self-assessed separately from the remaining **legal compatibility/authority** control. However **LE-02.02 must remain unproven** until the responsible project maintainer checks all third-party obligations, author provenance, and the media exception and signs a dated release-family review. Do not submit a 100% OpenSSF claim in advance.

## Individual release records

Complete SHA-256 digests are in the JSON inventory; the prefix below is a navigation aid, not sufficient for a verifier.

| Download | Type | SHA-256 prefix | Source correspondence / existing license |
| --- | --- | --- | --- |
| [resoarc-attachment-count-mobile-v0.1.4-rc10-20261019.zip](https://resoarc.com/downloads/resoarc-attachment-count-mobile-v0.1.4-rc10-20261019.zip) | Signed | `6f359dbaff4f37d4…` | NO exact source file in current Git tree |
| [resoarc-auto-number-signed-qa.zip](https://resoarc.com/downloads/resoarc-auto-number-signed-qa.zip) | Signed | `761224ac70ddd011…` | Full payload files match public Git tree |
| [resoarc-auto-number-v1.0.0.zip](https://resoarc.com/downloads/resoarc-auto-number-v1.0.0.zip) | Signed | `fd7d0873f8ebf755…` | Partial: 3/8 files |
| [resoarc-auto-number-v1.1.0-beta.zip](https://resoarc.com/downloads/resoarc-auto-number-v1.1.0-beta.zip) | Signed | `c2de1c7735e8c32a…` | Partial: 6/8 files |
| [resoarc-backup-migration-v1.0.0-source.zip](https://resoarc.com/downloads/resoarc-backup-migration-v1.0.0-source.zip) | Source | `06648e849bb38b9d…` | License in source ZIP |
| [resoarc-backup-migration-v1.0.0.zip](https://resoarc.com/downloads/resoarc-backup-migration-v1.0.0.zip) | Source | `ab858430620f1bd2…` | License in source ZIP |
| [resoarc-conditional-format-signed-qa.zip](https://resoarc.com/downloads/resoarc-conditional-format-signed-qa.zip) | Signed | `b9a0d7db277e8efb…` | Full payload files match public Git tree |
| [resoarc-conditional-format-v0.1.0-alpha-source.zip](https://resoarc.com/downloads/resoarc-conditional-format-v0.1.0-alpha-source.zip) | Source | `64ef943d7c302bd7…` | License in source ZIP |
| [resoarc-conditional-signed-qa.zip](https://resoarc.com/downloads/resoarc-conditional-signed-qa.zip) | Signed | `1f706267511884ff…` | Full payload files match public Git tree |
| [resoarc-csv-export-mobile-v0.1.5-rc10-20261019.zip](https://resoarc.com/downloads/resoarc-csv-export-mobile-v0.1.5-rc10-20261019.zip) | Signed | `234ec6d8917c25bd…` | NO exact source file in current Git tree |
| [resoarc-date-calculator-signed-qa.zip](https://resoarc.com/downloads/resoarc-date-calculator-signed-qa.zip) | Signed | `b2d74dcb6467d440…` | Full payload files match public Git tree |
| [resoarc-date-calculator-v0.1.0-alpha-source.zip](https://resoarc.com/downloads/resoarc-date-calculator-v0.1.0-alpha-source.zip) | Source | `251fcb2bdcb7a7d8…` | License in source ZIP |
| [resoarc-field-help-mobile-v0.1.3-rc-20261018.zip](https://resoarc.com/downloads/resoarc-field-help-mobile-v0.1.3-rc-20261018.zip) | Signed | `5c49a688ca878a47…` | NO exact source file in current Git tree |
| [resoarc-grid-editor-signed-qa.zip](https://resoarc.com/downloads/resoarc-grid-editor-signed-qa.zip) | Signed | `391568b0381fb99c…` | Full payload files match public Git tree |
| [resoarc-grid-editor-v0.1.0-alpha-source.zip](https://resoarc.com/downloads/resoarc-grid-editor-v0.1.0-alpha-source.zip) | Source | `fb806021a2947dea…` | License in source ZIP |
| [resoarc-kanban-signed-qa.zip](https://resoarc.com/downloads/resoarc-kanban-signed-qa.zip) | Signed | `4d16cd3a8145d543…` | Full payload files match public Git tree |
| [resoarc-kanban-v0.1.0-alpha-source.zip](https://resoarc.com/downloads/resoarc-kanban-v0.1.0-alpha-source.zip) | Source | `41216d6bd4bdc091…` | License in source ZIP |
| [resoarc-list-aggregate-mobile-v0.1.4-rc10-20261019.zip](https://resoarc.com/downloads/resoarc-list-aggregate-mobile-v0.1.4-rc10-20261019.zip) | Signed | `9a6ffe625769f51d…` | NO exact source file in current Git tree |
| [resoarc-list-search-signed-qa.zip](https://resoarc.com/downloads/resoarc-list-search-signed-qa.zip) | Signed | `f4aa2680f68b6c0a…` | Full payload files match public Git tree |
| [resoarc-list-search-v0.1.0-alpha-source.zip](https://resoarc.com/downloads/resoarc-list-search-v0.1.0-alpha-source.zip) | Source | `55967bf46daede50…` | License in source ZIP |
| [resoarc-lookup-suggest-mobile-v0.1.5-qa-20261018.zip](https://resoarc.com/downloads/resoarc-lookup-suggest-mobile-v0.1.5-qa-20261018.zip) | Signed | `d3b2c88810a2f5d0…` | NO exact source file in current Git tree |
| [resoarc-qr-code-mobile-v0.1.3-rc-20261018.zip](https://resoarc.com/downloads/resoarc-qr-code-mobile-v0.1.3-rc-20261018.zip) | Signed | `78299ed5ac81d134…` | NO exact source file in current Git tree |
| [resoarc-record-toc-mobile-v0.1.3-rc-20261018.zip](https://resoarc.com/downloads/resoarc-record-toc-mobile-v0.1.3-rc-20261018.zip) | Signed | `6ba55dbc1b500bc4…` | NO exact source file in current Git tree |
| [resoarc-related-links-mobile-v0.1.3-rc-20261018.zip](https://resoarc.com/downloads/resoarc-related-links-mobile-v0.1.3-rc-20261018.zip) | Signed | `3a66cb126a16715e…` | NO exact source file in current Git tree |
| [resoarc-save-navigation-mobile-v0.1.3-rc-20261018.zip](https://resoarc.com/downloads/resoarc-save-navigation-mobile-v0.1.3-rc-20261018.zip) | Signed | `6e281275e2eb276e…` | NO exact source file in current Git tree |
| [resoarc-site-20261017-recovered-source.zip](https://resoarc.com/downloads/resoarc-site-20261017-recovered-source.zip) | Source | `dda9d520cf2df37f…` | License in source ZIP |
| [resoarc-tabs-signed-qa.zip](https://resoarc.com/downloads/resoarc-tabs-signed-qa.zip) | Signed | `5a9847558a71af67…` | Full payload files match public Git tree |
| [resoarc-tabs-v0.1.0-beta.zip](https://resoarc.com/downloads/resoarc-tabs-v0.1.0-beta.zip) | Signed | `5eba44271945185e…` | Partial: 7/8 files |
| [resoarc-tabs-v1.0.0-20261021.zip](https://resoarc.com/downloads/resoarc-tabs-v1.0.0-20261021.zip) | Signed | `6be4e194acd495a2…` | Partial: 5/8 files |
| [resoarc-tabs-v1.0.0-signed-package-source.zip](https://resoarc.com/downloads/resoarc-tabs-v1.0.0-signed-package-source.zip) | Source | `a2a40a3042864d1d…` | License in source ZIP |
| [resoarc-text-normalizer-mobile-v0.1.4-rc10-20261019.zip](https://resoarc.com/downloads/resoarc-text-normalizer-mobile-v0.1.4-rc10-20261019.zip) | Signed | `16d4e43df291d033…` | NO exact source file in current Git tree |
| [resoarc-web8-v1.0.0-source.zip](https://resoarc.com/downloads/resoarc-web8-v1.0.0-source.zip) | Source | `d9bee5d112c706b3…` | License in source ZIP |
| [resoarcos-pc-v0.1.0-dev-source.zip](https://resoarc.com/downloads/resoarcos-pc-v0.1.0-dev-source.zip) | Source | `72b427a8ef08ab38…` | License in source ZIP |
| [resoarcos-pc-v0.1.1-dev-source.zip](https://resoarc.com/downloads/resoarcos-pc-v0.1.1-dev-source.zip) | Source | `ad60fd5629e91ae4…` | License in source ZIP |
| [resoarcos-pi-firstboot-v0.2.1-alpha-source.zip](https://resoarc.com/downloads/resoarcos-pi-firstboot-v0.2.1-alpha-source.zip) | Source | `d8beeccf39f457b4…` | License in source ZIP |

## Final acceptance record

- [x] 35 public ZIPs, same hashes on 3 official hosts.
- [x] Exact MIT LICENSE and NOTICE, same 3 hosts.
- [x] Detailed software-component license discovery, including QR MIT+Apache 2.0 and Backup fflate MIT.
- [x] Documented 8 full / 4 partial / 10 absent source-to-signed payload mapping.
- [ ] Public license catalog and companion notices are verified **in production after deployment**.
- [ ] Full origin and modification/redistribution rights for the 14 partially/unmatched signed versions approved and documented by an accountable maintainer.
- [ ] Media rights and any exceptional upstream notices checked for source snapshot before declaring all released software legally compatible.
- [ ] Official issuer questionnaire updated only for actual passing controls. No independent OpenSSF certification claimed.

**Issue:** [Production-source and release license follow-up #74](https://github.com/resoarc/resoarc-site/issues/74).
