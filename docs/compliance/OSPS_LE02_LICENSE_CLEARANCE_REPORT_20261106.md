# OpenSSF LE-02.02: released software rights and license closure report

**Date of evidence:** 2026-11-06 JST. **Decision:** HOLD.  
**Official [OpenSSF project #15597](https://www.bestpractices.dev/projects/15597/baseline-1):** 96% (23/24), LE-03.02 Met, **LE-02.02 Unmet**. A formal badge has not been earned.

## Scope and established technical evidence

- **35 public ZIPs**, consisting of **22 signed kintone installers** and **13 source/other ZIPs**. All **105** observed downloads on `resoarc.com`, `www.resoarc.com`, and `resoarc.pages.dev` match recorded SHA-256 and bytes. **6/6** LICENSE/NOTICE documents also match; [production release-and-license index](https://resoarc.com/downloads/) lists all 35 products. [Primary public inventory](OSPS_RELEASE_35_LICENSE_INVENTORY_20261106.json).
- Declared original implementation license is **MIT**; the QR Code mobile plugin retains **Kazuhiko Arase's MIT copyright and Apache 2.0 text** in `contents.zip/js/qr-lib.js`. Backup & Migration embeds **fflate 0.8.3 MIT** and `LICENSES/fflate-MIT.txt`; **esbuild MIT** is build-only. The recovered site source contains separately licensed **OFL font and Unsplash photo**. These do not become MIT material through packaging. [Detailed license review](OSPS_RELEASE_35_LICENSE_EVIDENCE_20261106.md).
- These are **software-license identity and delivery checks**, not a complete independent legal determination of every copyright holder or transfer right. The official LE-02.02 requirement refers specifically to licenses for *released software assets*, not a blanket third-party audit certificate. [OpenSSF v2026.08.28](https://baseline.openssf.org/versions/2026-08-28.html).

## Actual signed-payload provenance findings

[22-release machine-readable evidence](OSPS_LE02_SIGNED22_PROVENANCE_REVIEW_20261106.json) compares **each actual signed package's nested contents** against two independent evidence categories:

| Evidence category | All embedded files match | Some match | No matching file / candidate |
| --- | ---: | ---: | ---: |
| Public Codeberg Git tree and checked Git blobs at `8e279c5` | 8 | 4 | 10 |
| Seven preserved private QA release snapshots | 12 | 6 | 4 |

**The rows are different types of evidence, not additive counts.** A complete QA-archive match means that the same executable/configuration payload was preserved earlier in a dated internal QA ZIP; it is not independent proof of original authorship or rights to redistribute. The archived signing keys and any protected material were **not copied into this public report**.

### Comparison against all 13 publicly downloadable source archives

A separate byte-level check across **all 13 actual released source ZIPs**, not just the latest public Git tree, produced **9/22 full matches, 3/22 partial matches, and 10/22 without a matched source file**. This reveals an exact distributable source counterpart for **Tabs v1.0.0 (8/8 files)**, which had previously shown only a partial match to the current public Codeberg Git tree. The four different "missing source" measures should not be conflated.

- [13-source-to-22-signed comparison, exact SHA-256 per nested member](OSPS_13_SOURCE_ZIPS_TO_22_SIGNED_MATCH_20261106.json).
- **Technical scope**: shared byte-identical content in published source archives, not proof of the originator's copyright permission. Only the original operator and, where required, third-party licensing counsel can approve the rights declaration.
- The **10 mobile release packages** lacking an exact counterpart in *any of the 13 public source ZIPs* remain traceable to private QA or formal signed release bundles in many cases; those private QA files are intentionally not misrepresented as already-public source code.

### Eight signed ZIPs with a formal historical release record

Two historical, four-product central release manifests (dated 2026-10-19) were inspected. For **all eight exact public ZIPs**, the old manifest SHA-256, current public bytes, signed-verification flag and historical formal approval ID agree.

- `CENTRAL-READONLY4-20261019`: field-help, qr-code, record-toc and related-links. Approval recorded as `CENTRAL-READONLY4-GO-20261019-03`; the original release includes MIT LICENSE, a NOTICE, installation/migration guide and release notes, each with a manifest-pinned SHA-256.
- `CENTRAL-WAVE2-4-20261019`: csv-export, lookup-suggest, list-aggregate and attachment-count. Approval recorded as `CENTRAL-PLUGIN-GO-WAVE2-20261019-02`; same four companion documents and verified release signatures.
- The document and manifest hashes for the historical releases are preserved in the [private-evidence digest fields](OSPS_LE02_SIGNED22_PROVENANCE_REVIEW_20261106.json); the internal archive and signing-key location are intentionally **not published**. A future external reviewer may inspect them under appropriate access conditions.

Historical approval to **publish the release** is not necessarily a legal opinion or universal confirmation of rights. It does, however, establish a dated accountable release process for those eight packages.

### Important negative evidence

A QA-only 28-plugin snapshot dated 2026-10-18 explicitly says `rightsApproved: false`, `centralReleaseGo: false`, and `distributionAllowed: false`. Its bundles must never be represented as approved production releases simply because their code resembles a later version. The eight manifests above have their own later approval records, but a distinct owner rights attestation for the **entire 35-asset scope** remains outstanding.

## What must be documented before LE-02.02 may be marked Met

1. **Source authority for the 14 incomplete public Git matches:** retain the exact candidate source-build records, or deliberately publish accurately labeled extracted-source snapshots while retaining the original signed ZIPs; record author/contributor identity internally, authorizations to place code under MIT, and all imported third-party code. Do not claim that a generated snapshot reconstructs lost development history.
2. **All 35 released-software assets:** verify that each executable/bundle/component was made available under an OSI- or FSF-compliant software license; resolve any restrictive exception. Distinguish third-party *media* such as OFL fonts and Unsplash imagery and consider a software-only source snapshot if the media conditions cannot be represented correctly.
3. **Reviewer accountability:** the responsible ResoArc operator must sign a dated asset-by-asset or clearly scoped release-family license decision after actually inspecting source ownership and third-party obligations. An AI, automated scanner, old `rightsApproved: false` QA manifest, or technical checksum cannot be used as a human sign-off. Escalate doubtful upstream rights, patents or attribution to a qualified legal adviser.
4. **Evidence link and official submission:** preserve proof of that decision with a clear timestamp and version boundaries, then update only LE-02.02 on OpenSSF's self-assessment. The voluntary self-assessment is not external certification.

## External legal contact status

A 2026-10-26 reply to ResoArc's prior enquiry from a Tokyo intellectual-property support center explained that its free consultation targets local businesses/sole proprietors or people planning to start businesses, and excludes noncommercial non-profit projects without qualifying business plans. It offered software-capable advisers **only if eligible**. This response is an **eligibility clarification**, not a product rights clearance or legal assessment. Seek an appropriate channel for a noncommercial individual OSS project instead of asserting a legal review happened.

## Acceptance gates for automated evidence

- [x] All 35 public ZIPs and MIT/NOTICE sidecars available, SHA-256 verified
- [x] QR, fflate, build-time and site-media licensing identified
- [x] All 22 signed nested payloads evaluated against public Git and QA archives
- [x] Eight signed assets matched to historically approved formal release manifests with actual original companion files
- [ ] Exact source/rights chain fully documented for the remaining portions of 14 signed assets
- [ ] Specific rights and license decision approved by the real project operator for every software release family
- [ ] Any media/legal exceptions resolved or excluded from the software distribution scope
- [ ] Official LE-02.02 moved from Unmet to Met **only after the previous gates**

**No all-clear, independent audit, earned badge, or legal advice is represented here.** Follow-up: [issue #74](https://github.com/resoarc/resoarc-site/issues/74).
